from typing import Dict, Any, List, Tuple
import black

from agent.tools import Toolset
from agent.prompts import SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT, get_current_code_and_tests_prompt_part, \
    get_task_header, get_llm_prompt


class ReActLoop:
    def __init__(self, llm, tools: Toolset, max_iters: int):
        self.llm = llm
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
            tests_output_prompt = f"\n```\n{tests_output.strip()}\n```"
        return "Some tests failed, analyze error and iterate on solution.", tests_output_prompt

    def _call_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "Patch":
            return self.tools.write_file(**args).output
        return f"Unknown tool: {name}"

    def run(self) -> Dict[str, Any]:
        problem_explanation = "\n\n".join([SYSTEM_PROMPT, REACT_INSTRUCTIONS, FEW_SHOT, get_task_header()])
        self.trajectory = []

        trajectory_test_run_analysis, test_run_results = self._get_test_run_result({})
        self.trajectory.append(f"Observation: {trajectory_test_run_analysis}")

        for i in range(self.max_iters):
            print("Iteration:", i + 1, "/", self.max_iters)

            llm_prompt = get_llm_prompt(
                python_code=self.tools.open_file("task.py").output.strip(),
                python_tests=self.tools.open_file("test_task.py").output.strip(),
                tests_run_result=test_run_results,
                problem_explanation=problem_explanation,
                current_trajectory=self.trajectory,
            )

            print("1. LLM Prompt:")
            print(llm_prompt)
            completion = self.llm(llm_prompt)
            print("2. LLM Completion:")
            print(completion)
            print("--------------------------------")

            # Parse last action block
            action_name, action_args, trajectory_line = parse_action(completion)
            self.trajectory.append(trajectory_line)
            if action_name == "Finish":
                print(" -> finishing, trajectory:")
                print("\n".join(self.trajectory))
                return {"status": "done", "trajectory": self.trajectory}

            obs = self._call_tool(action_name, action_args)
            trajectory_test_run_analysis, test_run_results = self._get_test_run_result({})
            self.trajectory.append(f"Observation: {obs} {trajectory_test_run_analysis}")

        print(" -> budget exhausted, trajectory:")
        print("\n- ".join(self.trajectory))
        return {"status": "budget_exhausted", "trajectory": self.trajectory}


def parse_action(block: str) -> tuple[str, dict, str]:
    import json, re

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


def truncate(s: str, limit: int = 4000) -> str:
    return s if len(s) <= limit else s[:limit] + "\n...[truncated]..."


if __name__ == "__main__":
    text = """
I need to do some changes to the code. The solution is to remove a line.
Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]
"""

    print(parse_action(text))



# if __name__ == "__main__":
#     text = """
# def has_close_elements(numbers: List[float], threshold: float) -> bool:
#     '''
# Check if in given list of numbers, are any two numbers closer to each other than
# given threshold.
# >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
# False
# >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
# True
#     '''
#     for idx, elem in enumerate(numbers):
#         for idx2, elem2 in enumerate(numbers):
#             if idx != idx2:
#                 distance = elem - elem2
#                 if distance < threshold:
#                     return True
# return True
#
#     # return False
#     """
#
#     formatted = black.format_str(text, mode=black.Mode(
#         target_versions = {black.TargetVersion.PY36},
#         # line_length = 10,
#         string_normalization = False,
#         is_pyi = False,
#     ))
#     print(formatted)
