from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import StateGraph, START, END

from agent.prompts import build_thought_prompt, build_patch_prompt
from agent.parsers import parse_thought, parse_patch
from agent.tools import Toolset


class LoopState(TypedDict, total=False):
    # Immutable inputs (read as needed)
    code: str
    tests: str

    # Runtime
    trajectory: List[str]
    tests_run_prompt_block: str
    last_obs: str
    iterations: int
    status: Literal["running", "done", "budget_exhausted"]

    # Intermediates
    thought_line: str


class LangGraphReActLoop:
    def __init__(self, llm_thought, llm_patch, tools: Toolset, max_iters: int):
        self.llm_thought = llm_thought
        self.llm_patch = llm_patch
        self.tools = tools
        self.max_iters = max_iters

    # ---------- helpers ----------

    def _open_code(self) -> str:
        return self.tools.open_file("task.py").output.strip()

    def _open_tests(self) -> str:
        return self.tools.open_file("raw_test_task.py").output.strip()

    def _run_tests_as_prompt_block(self) -> (str, str):
        res = self.tools.run_pytests()
        if res.ok:
            return "All tests passed.", "All tests passed."
        out = (res.output or "").strip()
        return "Some tests failed, analyze error and iterate on solution.", f"\n```text\n{out}\n```"

    def _init_state(self) -> LoopState:
        traj_msg, test_block = self._run_tests_as_prompt_block()
        status: Literal["running", "done"] = "done" if "All tests passed." in traj_msg else "running"
        return {
            "code": self._open_code(),
            "tests": self._open_tests(),
            "trajectory": [f"Observation: {traj_msg}"],
            "tests_run_prompt_block": test_block,
            "last_obs": traj_msg,
            "iterations": 0,
            "status": status,
        }

    # ---------- nodes ----------

    def node_thought(self, state: LoopState) -> LoopState:
        if state["iterations"] >= self.max_iters:
            state["status"] = "budget_exhausted"
            return state

        thought_prompt = build_thought_prompt(
            python_code=self._open_code(),
            python_tests=self._open_tests(),
            tests_run_result=state["tests_run_prompt_block"],
            current_trajectory=state["trajectory"],
        )
        out = self.llm_thought(thought_prompt)
        print(" -> LLM completion thought output:\n", out)
        # parse
        try:
            kind, payload, matched = parse_thought(out)
        except Exception as e:
            print(f" -> error parsing Thought output '{out}':", e)
            kind, payload = "Thought", {"text": "Error parsing your Thought output, retry and ensure it follows the format exactly."}

        line = f"{kind}: {payload['text']}"
        state["trajectory"].append(line)
        state["thought_line"] = line
        return state

    def node_patch(self, state: LoopState) -> LoopState:
        if not state.get("thought_line"):
            return state

        patch_prompt = build_patch_prompt(
            python_code=self._open_code(),
            python_tests=self._open_tests(),
            tests_run_result=state["tests_run_prompt_block"],
            thought_line=state["thought_line"],
            current_trajectory=state["trajectory"],
        )
        out = self.llm_patch(patch_prompt)
        print(" -> LLM completion patch output:\n", out)

        # parse + apply
        try:
            kind, patch_args, matched = parse_patch(out)
            state["trajectory"].append(f"Action: Patch[{patch_args}]")
            obs = self.tools.write_file(**patch_args).output
        except Exception as e:
            print(f" -> error parsing Patch output with patch input '{out}':", e)
            obs = f"Error parsing your Patch output, retry and ensure it follows the format exactly."

        # re-run tests
        traj_msg, test_block = self._run_tests_as_prompt_block()
        state["tests_run_prompt_block"] = test_block
        state["last_obs"] = traj_msg
        state["trajectory"].append(f"Observation: {obs} {traj_msg}")
        state["iterations"] += 1

        if "All tests passed." in traj_msg:
            state["status"] = "done"
        return state

    # ---------- run ----------

    def run(self) -> Dict[str, Any]:
        initial = self._init_state()
        if initial["status"] == "done":
            return {"status": "done", "trajectory": initial["trajectory"]}

        graph = StateGraph(LoopState)
        graph.add_node("thought", self.node_thought)
        graph.add_node("patch", self.node_patch)

        # START -> thought -> patch -> (thought | END)
        graph.add_edge(START, "thought")
        graph.add_edge("thought", "patch")

        def router(state: LoopState) -> str:
            if state["status"] == "done":
                return END
            if state["iterations"] >= self.max_iters:
                state["status"] = "budget_exhausted"
                return END
            return "thought"

        graph.add_conditional_edges("patch", router, {"thought": "thought", END: END})

        app = graph.compile()
        final: LoopState = app.invoke(initial)

        print(f"Final trajectory:\n" + "\n".join(final["trajectory"]))
        print(f"Final status: {final['status']}")
        return {
            "status": final["status"],
            "trajectory": final["trajectory"],
        }
