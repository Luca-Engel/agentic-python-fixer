import json
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
                python_tests=self.tools.open_file("test_task.py").output.strip(),
                tests_run_result=test_run_results,
                current_trajectory=self.trajectory,
            )
            print("1. Thought Prompt:\n", thought_prompt)
            thought_out = self.llm_thought(thought_prompt)
            print("2. Thought Completion:\n", thought_out)

            try:
                kind, payload, matched = _parse_thought_or_finish(thought_out)
            except Exception as e:
                print(" -> error parsing Thought/Finish output:", e)
                self.trajectory.append(f"Error parsing your Thought output, retry and ensure it is concise and follows the format exactly.")
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
                python_tests=self.tools.open_file("test_task.py").output.strip(),
                tests_run_result=test_run_results,
                thought_line=thought_line,
                current_trajectory=self.trajectory,
            )
            print("3. Patch Prompt:\n", patch_prompt)
            patch_out = self.llm_patch(patch_prompt)
            print("4. Patch Completion:\n", patch_out)

            kind, patch_args, matched = _parse_patch(patch_out)
            self.trajectory.append(f"Action: Patch[{json.dumps(patch_args, separators=(',', ':'))}]")

            obs = self.tools.write_file(**patch_args).output

            # re-run tests
            traj_test_msg, test_run_results = self._get_test_run_result({})
            self.trajectory.append(f"Observation: {obs} {traj_test_msg}")
            if "All tests passed." in traj_test_msg:
                break


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


def _parse_thought_or_finish(block: str) -> tuple[str, dict, str]:
    """
    Accepts exactly one line:
      - Finish[{"message":"..."}]
      - Thought[...]
    Returns: (name, args, matched)
      - Finish -> args is the parsed JSON object (must contain "message": str)
      - Thought -> args is {"text": "<sentence>"}
    """
    import json, re

    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    i = len(lines) - 1
    name = ""
    inner = ""
    matched = ""
    while i >= 0:
        line = lines[i]
        m = re.match(r'^(\w+)\[(.*)\]$', line, re.S)
        if not m:
            m2 = re.match(r'^Thought:\s*(.+)$', line)
            if not m2:
                i -= 1
                continue
            name = "Thought"
            inner = m2.group(1)
            matched = m2.group(0).strip()
        else:
            name, inner = m.group(1), m.group(2)
            matched = m.group(0).strip()

        if name in ("Finish", "Thought"):
            break


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

    raise ValueError("Unknown action for this stage: expected Finish or Thought.")


def _parse_patch(block: str) -> tuple[str, dict, str]:
    """
    Accepts exactly one line:
      - Patch[{"start":<int>,"end":<int>,"text":"<new code>"}]
    Returns: (name, args, matched) with args validated.
    """
    import json, re

    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
    i = len(lines) - 1
    inner = ""
    matched = ""
    while i >= 0:
        line = lines[i]
        m = re.match(r'^Patch\[(.*)\]$', line, re.S)
        if not m:
            i -= 1
            continue

        inner = m.group(1).strip()
        matched = m.group(0).strip()
        break



    # if len(lines) != 1:
    #     raise ValueError("Patch agent must output exactly one non-empty line.")
    # line = lines[0]

    # m = re.match(r'^Patch\[(.*)\]$', line, re.S)
    # if not m:
    #     raise ValueError("Expected a single 'Patch[...]' line.")
    # inner = m.group(1).strip()
    # matched = m.group(0).strip()

    args = {} if inner == "" else json.loads(inner)
    if not isinstance(args, dict):
        raise ValueError("Patch[...] must contain a JSON object.")

    # Validate required keys
    for key in ("start", "end", "text"):
        if key not in args:
            raise ValueError(f"Patch missing required key '{key}'.")
    # Coerce/validate types
    try:
        args["start"] = int(args["start"])
        args["end"] = int(args["end"])
        args["nb_indents"] = int(args.get("nb_indents", 0))
    except Exception:
        raise ValueError("'start' and 'end' must be integers.")
    if not isinstance(args["text"], str):
        raise ValueError("'text' must be a string.")

    return "Patch", args, matched


if __name__ == "__main__":
    print("\n    hello\n\n".strip())
    print("----")


    unformatted = """
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
                distance = abs(elem - elem2)
                distance = elem - elem2
                if distance < threshold:
                    return True

    return False"""
    print(black.format_str(unformatted, mode=black.Mode()))

# if __name__ == "__main__":
#     text = """
# I need to do some changes to the code. The solution is to remove a line.
# Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]
# """
#
#     print(parse_action(text))



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
