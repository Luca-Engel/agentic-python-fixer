from collections.abc import Callable
from typing import Dict, Any, List

from agent.tools import Toolset
from .prompts import SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT


class ReActLoop:
    def __init__(self, llm, tools: Toolset, max_iters: int):
        self.llm = llm
        self.tools = tools
        self.max_iters = max_iters
        self.trajectory: List[str] = []

    def _call_tool(self, name: str, args: Dict[str, Any]) -> str:
        # if name == "open_file":
        #     return self.tools.open_file(**args).output
        if name == "Patch":
            return self.tools.write_file(**args).output
        if name == "RunPytests":
            tests_output = self.tools.run_pytests(**args).output
            tests_output_prompt = f"running the tests produced the following output: ```\n{tests_output}\n```"
            return tests_output_prompt
        # if name == "search_repo":
        #     return self.tools.search_repo(**args).output
        return f"Unknown tool: {name}"

    def run(self, task_header: str) -> Dict[str, Any]:
        prompt = "\n\n".join([SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT, task_header])
        transcript = prompt
        print(f"LLM prompt:\n{prompt}\n{'-'*40}")
        for i in range(self.max_iters):
            print(f"transcript at {i}:{transcript}")
            completion = self.llm(transcript)  # returns appended 'Thought/Action/ActionInput'
            print("model completion:")
            print(completion)
            print("--------------------------------")
            self.trajectory.append(completion)

            # Parse last action block
            action_name, action_args = parse_action(completion)
            if action_name == "Finish":
                return {"status": "done", "trajectory": self.trajectory}

            obs = self._call_tool(action_name, action_args)
            transcript += f"\nObservation: {truncate(obs)}"
        return {"status": "budget_exhausted", "trajectory": self.trajectory}


# def parse_action(block: str):
#     # very simple extraction; replace with robust parser for production
#     import json, re
#     print("parsing action from block:", block)
#     name = re.search(r"Action:\s*(\w+)", block).group(1)
#     args = re.search(r"ActionInput:\s*(\{.*\})", block, re.S).group(1)
#     return name, json.loads(args)

def parse_action(block: str):
    import json, re
    print("parsing action from block:", block)
    match = re.search(r"(\w+)\[(.*)\]", block, re.S)
    if not match:
        raise ValueError("No action found")
    name, arg = match.group(1), match.group(2)
    if name == "Patch":
        args = json.loads(arg)
    elif name == "RunPytests":
        args = {}
    elif name == "Finish":
        args = {}
    else:
        raise ValueError(f"Unknown action: {name}")
    return name, args


def truncate(s: str, limit: int = 4000) -> str:
    return s if len(s) <= limit else s[:limit] + "\n...[truncated]..."


if __name__ == "__main__":
    text = """

Thought: Run all tests.
Action: run_pytests
ActionInput: {}

Thought: Stop.
Action: finish
ActionInput: {}"""

    print(parse_action(text))