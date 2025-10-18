SYSTEM_PROMPT = """You are a Python bug-fixing assistant.
You will iteratively: (1) analyze code/tests and failure traces, (2) propose small patches,
(3) re-run tests, (4) stop when tests pass. Keep changes minimal and safe."""

REACT_INSTRUCTIONS = """
Strict ReAct format (ONE thought and ONE action per iteration — parser-enforced):

- Output exactly ONE line starting with `Thought:` and exactly ONE line starting with `Action:`. No other `Thought` or `Action` lines allowed.
- `Thought:` must be a single brief sentence on one line (no newlines).
- `Action:` must be on a single line and use the form: ActionName[<compact JSON>]
  - The JSON inside brackets must be valid compact JSON (no unescaped newlines).
  - Allowed ActionName values: Patch, Finish.
  - For multiple edits do the first edit now, then the next edit in the next iteration, etc.
- Do not include any extra narration, code fences, or surrounding text. Output must be strictly the two lines described.

Allowed actions:
- Patch[{"start": <int>, "end": <int>, "text": "<new code>"}]
        (*`start`* and *`end`* are the line offsets in the file (1-based).
         To **replace** an existing line with index `x`, set `"start": x` and `"end": x+1`.
         To **insert** a new line *before* the current line `x`, set `"start": x` and `"end": x`.
         `text` is the new content (may contain multiple lines) that will replace the range.
         Ensure that the indentation of `text` matches the surrounding code.)
- Finish[<brief summary of the fix>]

Examples — valid:
Thought: The test fails because line 12 does not return 0. Replace this line with the correct return statement.
Action: Patch[{"start":12,"end":13,"text":"    return 0 \n"}]

Examples — invalid (will be rejected by the parser):
Thought: First thought.
Thought: Second thought.
Action: Patch[{"start":4,"end":4,"text":"    sum = a + b \n"}]

Repeat this pattern until tests pass, then call:
Thought: All tests passed; <brief summary of fixes>.
Action: Finish[{"message":"brief summary"}]
"""

FEW_SHOT = r"""
# Example
Question: The code shown below (always the updated version is displayed, so if you have previously changed something, these changes will be included in the code below) has a bug.
When executing its tests, the following output is produced:
<output of failed tests omitted for brevity>
Thought: The if statement is currently '>' but needs to be '>='. change this
Action: Patch[{"start" : 12, "end" : 12, "text":"    if value_1 >= value_2:\n"}]
Observation: Patch applied. All tests passed.
Thought: Done.
Action: Finish[]

The current code is as follows (line numbers are added for clarity but you should provide the fix with ONLY THE CODE):
<numbered code omitted for brevity>
The tests are as follows:
<tests omitted for brevity>
"""


def get_task_header() -> str:
    return (
        f"Question: The code shown below (always the updated version is displayed, "
        f"so if you have previously changed something, these changes will be included in the code below) "
        f"may have a bug.\n"
        f"The output of execits tests is also displayed below (again, always the latest output after your changes)"
    )


def get_current_code_and_tests_prompt_part(python_code: str, python_tests: str, tests_run_result: str) -> str:
    python_code_lines = python_code.splitlines()
    numbered_code = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(python_code_lines))

    return (
            "\n\nThe current code is as follows "
            "(line numbers are added for clarity provide the fix with ONLY THE CODE):\n"
            + f"```Python\n{numbered_code}\n```"
            + "\n\nThe tests are as follows:\n"
            + f"```Python\n{python_tests}\n```"
            + f"\n\nLatest test run output: {tests_run_result}"
    )
