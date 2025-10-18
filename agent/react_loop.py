from typing import Dict, Any, List
import black

from agent.tools import Toolset
from agent.prompts import SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT, get_current_code_and_tests_prompt_part


class ReActLoop:
    def __init__(self, llm, tools: Toolset, max_iters: int):
        self.llm = llm
        self.tools = tools
        self.max_iters = max_iters
        self.trajectory: List[str] = []

    def _get_test_run_result(self, args: Dict[str, Any]) -> str:
        test_tool_res = self.tools.run_pytests(**args)
        tests_output = test_tool_res.output
        all_tests_passed = test_tool_res.ok
        if all_tests_passed:
            return "All tests passed."
        else:
            tests_output_prompt = f"\n```\n{tests_output.strip()}\n```"
        return tests_output_prompt

    def _call_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "Patch":
            return self.tools.write_file(**args).output
        return f"Unknown tool: {name}"

    def run(self, task_header: str) -> Dict[str, Any]:
        prompt = "\n\n".join([SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT, task_header])
        transcript = prompt
        for i in range(self.max_iters):
            print("Iteration:", i + 1, "/", self.max_iters)

            current_code_and_tests = get_current_code_and_tests_prompt_part(
                python_code=self.tools.open_file("task.py").output.strip(),
                python_tests=self.tools.open_file("test_task.py").output.strip(),
                tests_run_result=self._get_test_run_result({}),
            )


            print("1. LLM Prompt:")
            print(transcript + current_code_and_tests)
            completion = self.llm(transcript + current_code_and_tests)  # returns appended 'Thought/Action/ActionInput'
            print("2. LLM Completion:")
            print(completion)
            print("--------------------------------")
            self.trajectory.append(completion)

            # Parse last action block
            action_name, action_args = parse_action(completion)
            if action_name == "Finish":
                print(" -> finishing, trajectory:")
                print("\n- ".join(self.trajectory))
                return {"status": "done", "trajectory": self.trajectory}

            obs = self._call_tool(action_name, action_args)
            transcript += f"\nObservation: {truncate(obs)}"

        print(" -> budget exhausted, trajectory:")
        print("\n- ".join(self.trajectory))
        return {"status": "budget_exhausted", "trajectory": self.trajectory}


def parse_action(block: str):
    import json, re
    match = re.search(r"(\w+)\[(.*)\]", block, re.S)
    if not match:
        raise ValueError("No action found")
    name, arg = match.group(1), match.group(2)
    if name == "Patch":
        print(" -> patching with arg:", arg)
        args = json.loads(arg)
    elif name == "Finish":
        args = {}
    else:
        raise ValueError(f"Unknown action: {name}")
    return name, args


def parse_action(block: str) -> tuple[str, dict, str]:
    import json, re

    match = re.search(r"(\w+)\[(.*)\]", block, re.S)
    if not match:
        raise ValueError("No action found")

    matched = match.group(0)  # e.g. `Finish[...]`
    name, arg = match.group(1), match.group(2)

    if name == "Patch":
        print(" -> patching with arg:", arg)
        args = json.loads(arg)
    elif name == "Finish":
        args = {}
    else:
        raise ValueError(f"Unknown action: {name}")

    return name, args, matched


def truncate(s: str, limit: int = 4000) -> str:
    return s if len(s) <= limit else s[:limit] + "\n...[truncated]..."


# if __name__ == "__main__":
#     text = """
#
# Thought: Run all tests.
# Action: run_pytests
# ActionInput: {}
#
# Thought: Stop.
# Action: finish
# ActionInput: {}"""
#
#     print(parse_action(text))



if __name__ == "__main__":
    text = """
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    '''
Check if in given list of numbers, are any two numbers closer to each other than
given threshold.
>>> has_close_elements([1.0, 2.0, 3.0], 0.5)
False
>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
True
    '''
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = elem - elem2
                if distance < threshold:
                    return True
return True

    # return False
    """

    formatted = black.format_str(text, mode=black.Mode(
        target_versions = {black.TargetVersion.PY36},
        # line_length = 10,
        string_normalization = False,
        is_pyi = False,
    ))
    print(formatted)
