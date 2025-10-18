SYSTEM_PROMPT = """You are a Python bug-fixing assistant.
You will iteratively: (1) analyze code/tests and failure traces, (2) propose small patches,
(3) re-run tests, (4) stop when tests pass. Keep changes minimal and safe."""
#
# REACT_INSTRUCTIONS = r"""
# Strict ReAct format (ONE thought and ONE action per iteration — parser-enforced):
#
# - Output exactly ONE line starting with `Thought:` and exactly ONE line starting with `Action:`. No other `Thought` or `Action` lines allowed.
# - `Thought:` must be a single brief sentence on one line (no newlines).
# - `Action:` must be on a single line and use the form: ActionName[<compact JSON>]
#   - The JSON inside brackets must be valid compact JSON (no unescaped newlines).
#   - Allowed ActionName values: Patch, Finish.
#   - For multiple edits do the first edit now, then the next edit in the next iteration, etc.
# - Do not include any extra narration, code fences, or surrounding text. Output must be strictly the two lines described.
#
# Allowed actions:
# - Patch[{"start": <int>, "end": <int>, "text": "<new code>"}]
#         (*`start`* and *`end`* are the line offsets in the file (1-based).
#          To **replace** an existing line with index `x`, set `"start": x` and `"end": x+1`.
#          To **insert** a new line *before* the current line `x`, set `"start": x` and `"end": x`.
#          `text` is the new content (may contain multiple lines) that will replace the range.
#          Ensure that the indentation of `text` matches the surrounding code.)
# - Finish[<brief summary of the fix>]
#
# Examples — valid:
# Thought: The test fails because line 3 does not increment the index i. Add a line to increment i.
# Action: Patch[{"start":3,"end":3,"text":"    i += 1 \n"}]
#
# Examples — invalid (will be rejected by the parser):
# Thought: First thought.
# Thought: Second thought.
# Action: Patch[{"start":4,"end":4,"text":"    sum = a + b \n"}]
#
# Repeat this pattern until tests pass, then call:
# Thought: All tests passed; <brief summary of fixes>.
# Action: Finish[{"message":"brief summary"}]
# """
#
# FEW_SHOT = r"""
# # Example
# Question: The code shown below (always the updated version is displayed, so if you have previously changed something, these changes will be included in the code below) has a bug.
# When executing its tests, the following output is produced:
# <output of failed tests omitted for brevity>
# Thought: The if statement on line 12 is currently '>' but needs to be '>='. Fix this line.
# Action: Patch[{"start" : 12, "end" : 13, "text":"    if value_1 >= value_2: \n"}]
# Observation: Patch applied. All tests passed.
# Thought: Done.
# Action: Finish[]
#
# The current code is as follows (line numbers are added for clarity but you should provide the fix with ONLY THE CODE):
# <numbered code omitted for brevity>
# The tests are as follows:
# <tests omitted for brevity>
# """
#
#
# def get_task_header() -> str:
#     return (
#         f"Question: The code shown below (always the updated version is displayed, "
#         f"so if you have previously changed something, these changes will be included in the code below) "
#         f"may have a bug.\n"
#         f"The output of execits tests is also displayed below (again, always the latest output after your changes)"
#     )
#
#
# def get_current_code_and_tests_prompt_part(
#         python_code: str,
#         python_tests: str,
#         tests_run_result: str
# ) -> str:
#     python_code_lines = python_code.splitlines()
#     numbered_code = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(python_code_lines))
#
#     return (
#             "\n\nThe current code is as follows "
#             "(line numbers are added for clarity provide the fix with ONLY THE CODE):\n"
#             + f"```Python\n{numbered_code}\n```"
#             + "\n\nThe tests are as follows:\n"
#             + f"```Python\n{python_tests}\n```"
#             + f"\n\nLatest test run output: {tests_run_result}"
#     )
#
#
# def get_llm_prompt(
#         python_code: str,
#         python_tests: str,
#         tests_run_result: str,
#         problem_explanation: str,
#         current_trajectory: list,
# ) -> str:
#     current_code_and_tests = get_current_code_and_tests_prompt_part(
#         python_code=python_code,
#         python_tests=python_tests,
#         tests_run_result=tests_run_result,
#     )
#     prompt = problem_explanation
#     if current_trajectory:
#         prompt += "\n\nPrevious ReAct iterations:\n" + "\n".join(current_trajectory)
#     else:
#         prompt += "\n\nNo previous ReAct iterations yet, please start."
#     prompt += current_code_and_tests
#     return prompt


# --- ADD these to agent/prompts.py ---

THOUGHT_AGENT_INSTRUCTIONS = r"""
Please first reason about what your task is, then follow this strict output format — EXACTLY ONE LINE:
- If all tests pass: Finish[{"message":"<brief summary>"}]
- Otherwise: Thought[<single brief sentence describing the next minimal change>]

MAKE SURE TO FOLLOW THE FORMAT EXACTLY AND END YOUR OUTPUT WITH EITHER THE Finish[...] OR Thought[...] LINE.
"""

THOUGHT_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER ONE OF THESE TWO LINES:
- Thought[<single brief sentence describing the next minimal change>]
- Finish[{"message":"<brief summary>"}]
"""

PATCH_AGENT_INSTRUCTIONS = r"""
Please first reason about what your task is, then follow this strict output format — EXACTLY ONE LINE:
Patch[{"start":<int>,"end":<int>,"text":"<new code with newlines as needed>"}]

Note that
- *`start`* and *`end`* are the line offsets in the file (1-based).
- To **replace** an existing line with index `x`, set `"start": x` and `"end": x+1`.
- To **insert** a new line *before* the current line `x`, set `"start": x` and `"end": x`.
- `text` is the new content (may contain multiple lines) that will replace the range.
- Ensure that the indentation of `text` matches the surrounding code.)

MAKE SURE TO FOLLOW THE FORMAT EXACTLY AND END YOUR OUTPUT WITH THE Patch[...] LINE.
"""

PATCH_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER WITH THE Patch[...] LINE.
"""


def _format_code_and_tests(python_code: str, python_tests: str, tests_run_result: str) -> str:
    python_code_lines = python_code.splitlines()
    numbered_code = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(python_code_lines))
    return (
            "\n\nThe current code is as follows (line numbers are added for clarity; "
            "provide any fix with ONLY THE CODE content, not line numbers):\n"
            + f"```Python\n{numbered_code}\n```"
            + "\n\nThe tests are as follows:\n"
            + f"```Python\n{python_tests}\n```"
            + f"\n\nLatest test run output: {tests_run_result}"
    )


def build_thought_prompt(
        python_code: str,
        python_tests: str,
        tests_run_result: str,
        current_trajectory: list,
) -> str:
    # keep trajectory (last few lines) — this helps the model choose the next step
    traj = "\n".join(current_trajectory[-6:]) if current_trajectory else "No previous iterations."
    return (
            SYSTEM_PROMPT
            + "\n\nYou are the THOUGHT/FINISH agent."
            + THOUGHT_AGENT_INSTRUCTIONS
            + "\n\nPrevious steps (last few):\n" + traj
            + _format_code_and_tests(python_code, python_tests, tests_run_result)
            + THOUGHT_AGENT_QUICK_REMINDER
    )


def build_patch_prompt(
        python_code: str,
        python_tests: str,
        tests_run_result: str,
        thought_line: str,  # pass the literal "Thought: ..." line here
        current_trajectory: list,
) -> str:
    traj = "\n".join(current_trajectory) if current_trajectory else "No previous iterations."
    return (
            SYSTEM_PROMPT
            + "\n\nYou are the PATCH agent. Apply a single minimal patch that implements the Thought below."
            + PATCH_AGENT_INSTRUCTIONS
            + "\n\nThought to implement (verbatim):\n" + thought_line + "\n"
            + "Previous steps (last few):\n" + traj
            + _format_code_and_tests(python_code, python_tests, tests_run_result)
            + PATCH_AGENT_QUICK_REMINDER
    )