import json
import re
from typing import Dict, Any, List, Tuple

from agent.tools import Toolset
from agent.prompts import build_thought_prompt, build_patch_prompt
import black


class ReActLoop:
    def __init__(self, llm_thought, llm_patch, tools: Toolset, max_iters: int):
        self.llm_thought = llm_thought
        self.llm_patch = llm_patch
        self.tools = tools
        self.max_iters = max_iters
        self.trajectory: List[str] = []

    def _get_test_run_result(self, args: Dict[str, Any]) -> Tuple[str, str]:
        test_tool_res = self.tools.run_pytests(**args)
        tests_output = test_tool_res.output
        all_tests_passed = test_tool_res.ok
        if all_tests_passed:
            return "All tests passed.", "All tests passed."
        else:
            tests_output_prompt = f"\n```text\n{tests_output.strip()}\n```"
        return "Some tests failed, analyze error and iterate on solution.", tests_output_prompt

    def _call_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "Patch":
            return self.tools.write_file(**args).output
        return f"Unknown tool: {name}"

    def run(self) -> Dict[str, Any]:
        self.trajectory = []

        # initial test run
        traj_test_msg, test_run_results = self._get_test_run_result({})
        self.trajectory.append(f"Observation: {traj_test_msg}")
        if "All tests passed." in traj_test_msg:
            print(" -> all tests already passed, finishing.")
            return {"status": "done", "trajectory": self.trajectory}

        for i in range(self.max_iters):
            print("Iteration:", i + 1, "/", self.max_iters)

            # 1) THOUGHT/FINISH AGENT
            thought_prompt = build_thought_prompt(
                python_code=self.tools.open_file("task.py").output.strip(),
                python_tests=self.tools.open_file("raw_test_task.py").output.strip(),
                tests_run_result=test_run_results,
                current_trajectory=self.trajectory,
            )
            print("1. Thought Being prompted")
            thought_out = self.llm_thought(thought_prompt)
            print("2. Thought Completion:\n", thought_out)

            try:
                print("2.1 parsing thought")
                kind, payload, matched = _parse_thought(thought_out)
                print("2.2 thought parsed")
            except Exception as e:
                print(" -> error parsing Thought/Finish output:", e)
                self.trajectory.append(
                    f"Error parsing your Thought output, retry and ensure it is concise and follows the format exactly.")
                continue
            if kind == "Finish":
                self.trajectory.append(f"Action: Finish[{json.dumps(payload, separators=(',', ':'))}]")
                print(" -> finishing, trajectory:")
                print("\n".join(self.trajectory))
                return {"status": "done", "trajectory": self.trajectory}

            # kind == "thought"
            thought_line = f"Thought: {payload['text']}"
            self.trajectory.append(thought_line)

            # 2) PATCH AGENT
            patch_prompt = build_patch_prompt(
                python_code=self.tools.open_file("task.py").output.strip(),
                python_tests=self.tools.open_file("raw_test_task.py").output.strip(),
                tests_run_result=test_run_results,
                thought_line=thought_line,
                current_trajectory=self.trajectory,
            )
            print("3. Patch Being Prompted")
            patch_out = self.llm_patch(patch_prompt)
            print("4. Patch Completion:\n", patch_out)

            try:
                kind, patch_args, matched = _parse_patch(patch_out)
                self.trajectory.append(f"Action: Patch[{json.dumps(patch_args, separators=(',', ':'))}]")
                obs = self.tools.write_file(**patch_args).output
            except Exception as e:
                print(" -> error parsing Patch output:", e)
                self.trajectory.append(
                    f"Error parsing your Patch output, retry and ensure it follows the format exactly.")
                continue

            # re-run tests
            traj_test_msg, test_run_results = self._get_test_run_result({})
            self.trajectory.append(f"Observation: {obs} {traj_test_msg}")
            if "All tests passed." in traj_test_msg:
                print(" -> finishing, trajectory:")
                print("\n".join(self.trajectory))
                return {"status": "done", "trajectory": self.trajectory}

        print(" -> budget exhausted, trajectory:")
        print("\n- ".join(self.trajectory))
        return {"status": "budget_exhausted", "trajectory": self.trajectory}


def parse_action(block: str) -> tuple[str, dict, str]:
    match = re.search(r"(\w+)\[(.*)\]", block, re.S)
    if not match:
        raise ValueError("No action found")

    matched = match.group(0)  # e.g. `Finish[...]`
    name, arg = match.group(1), match.group(2)

    if name == "Thought":
        args = {}
    elif name == "Patch":
        print(" -> patching with arg:", arg)
        args = json.loads(arg)
    elif name == "Finish":
        args = {}
    else:
        raise ValueError(f"Unknown action: {name}")

    return name, args, matched


def _parse_thought(block: str) -> tuple[str, dict, str]:
    """
    Accepts exactly one line:
      - <random text allowed>Thought[...]
    Returns: (name, args, matched)
      - Thought -> args is {"text": "<sentence>"}
    """
    inner, matched, name = match_thought(block)

    if name == "Thought":
        content = inner.strip()
        # Accept either raw text or a quoted JSON string
        if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
            try:
                thought_text = json.loads(content)
            except Exception:
                # fall back to stripping quotes if json decoding fails
                thought_text = content[1:-1]
        else:
            thought_text = content

        if not isinstance(thought_text, str):
            raise ValueError("Thought[...] must contain a single brief string.")

        thought_text = thought_text.strip()
        if not thought_text:
            raise ValueError("Thought text must be non-empty.")

        if "\n" in thought_text:
            raise ValueError("Thought must be a single line (no newlines).")

        return "Thought", {"text": thought_text}, matched

    raise ValueError("Unknown action for this stage: expected Thought.")


def match_thought(block: str) -> tuple[str, str | Any, str]:
    """
    Matches the last occurrence of Thought[...] or Thought: ... in the given block.
    Returns: (inner, matched, name)
    """
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    i = len(lines) - 1
    name_ = ""
    inner_ = ""
    matched_ = ""
    while i >= 0:
        line_ = lines[i]
        m = re.search(r'Thought\[(.*)\]$', line_, re.S)
        if not m:
            m2 = re.search(r'Thought:\s*(.+)$', line_)
            if not m2:
                i -= 1
                continue
            name_ = "Thought"
            inner_ = m2.group(1)
            matched_ = m2.group(0).strip()
        else:
            name_ = "Thought"
            inner_ = m.group(1)
            matched_ = m.group(0).strip()

        if name_ in ("Thought"):
            break
        else:
            # e.g., if the LLM outputs Patch[...] here, look at previous line
            i -= 1
    return inner_, matched_, name_


def _parse_patch(block: str) -> tuple[str, dict, str]:
    """
    Accepts exactly one line:
      - Patch[{"start":<int>,"end":<int>,"text":"<new code>"}]
    Returns: (name, args, matched) with args validated.
    """
    inner_, matched_ = match_patch(block)

    args = {} if inner_ == "" else json.loads(inner_)
    if not isinstance(args, dict):
        raise ValueError("Patch[...] must contain a JSON object.")

    for key in ("start", "end", "text"):
        if key not in args:
            raise ValueError(f"Patch missing required key '{key}'.")

    try:
        args["start"] = int(args["start"])
        args["end"] = int(args["end"])
        args["nb_indents"] = int(args.get("nb_indents", 0))
    except Exception:
        raise ValueError("'start' and 'end' must be integers.")

    if not isinstance(args["text"], str):
        raise ValueError("'text' must be a string.")

    return "Patch", args, matched_


def match_patch(block: str) -> tuple[str, str]:
    """
    Matches the last occurrence of Patch[...] or Patch: {...} in the given block.
    Returns: (inner, matched)
    """
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    i = len(lines) - 1
    inner_ = ""
    matched_ = ""
    while i >= 0:
        line_ = lines[i]
        m = re.search(r'Patch\[(.*)\]', line_, re.S)
        if not m:
            m2 = re.search(r'Patch:\s*(\{.*\})', line_, re.S)
            if not m2:
                i -= 1
                continue
            inner_ = m2.group(1).strip()
            matched_ = m2.group(0).strip()
        else:
            inner_ = m.group(1).strip()
            matched_ = m.group(0).strip()
        break
    return inner_, matched_
