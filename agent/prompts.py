SYSTEM_PROMPT = """You are a Python bug-fixing assistant.
You will iteratively: (1) analyze code/tests and failure traces, (2) propose small patches,
(3) re-run tests, (4) stop when tests pass. Keep changes minimal and safe."""

REACT_INSTRUCTIONS = """
Strict ReAct format (ONE thought and ONE action per iteration — parser-enforced):

- Output exactly ONE line starting with `Thought:` and exactly ONE line starting with `Action:`. No other `Thought` or `Action` lines allowed.
- `Thought:` must be a single brief sentence on one line (no newlines).
- `Action:` must be on a single line and use the form: ActionName[<compact JSON>]
  - The JSON inside brackets must be valid compact JSON (no unescaped newlines).
  - Allowed ActionName values: Patch, RunPytests, Finish.
  - For multiple edits do the first edit now, then the next edit in the next iteration, etc.
- Do not include any extra narration, code fences, or surrounding text. Output must be strictly the two lines described.

Allowed actions:
- Patch[{"start": <int>, "end": <int>, "text": "<new code>"}]
        (use replace patches only; *`start`* and *`end`* are the line offsets in the file (0-based).
         To **replace** an existing line with index `x`, set `"start": x` and `"end": x+1`.
         To **insert** a new line *before* the current line `x`, set `"start": x` and `"end": x`.
         `text` is the new content (may contain multiple lines) that will replace the range.)
- RunPytests[]
- Finish[<brief summary of the fix>]

Examples — valid:
Thought: The test fails because line 12 does not return 0. Replace this line with the correct return statement.
Action: Patch[{"start":12,"end":13,"text":"    return 0\n"}]

Examples — invalid (will be rejected by the parser):
Thought: First thought.
Thought: Second thought.
Action: RunPytests[]
(or) Action: Patch[ ... ] followed by extra explanation lines.

Repeat this pattern until tests pass, then call:
Thought: All tests passed; summary.
Action: Finish[{"message":"brief summary"}]
"""
#   - For multiple edits use a single Patch action with an array of patch objects: Patch[{"patches":[{"start":..., "end":..., "text":"..."}]}]


FEW_SHOT = r"""
# Example
Question: The code shown below (always the updated version is displayed, so if you have previously changed something, these changes will be included in the code below) has a bug.
When executing its tests, the following output is produced:
<output of failed tests omitted for brevity>
Thought: The test says TypeError due to None. Add default return value.
Action: Patch[{"type":"replace","start":12,"end":12,"text":"    return 0\n"}]
Observation: Patch applied.
Thought: Re-run tests.
Action: RunPytests[]
Observation: All tests passed.
Thought: Done.
Action: Finish[]

The current code is as follows (line numbers are added for clarity but you should provide the fix with ONLY THE CODE):
<numbered code omitted for brevity>
The tests are as follows:
<tests omitted for brevity>
"""

def get_task_header(entire_buggy_code: str, tests_output: str) -> str:
    # return (f"Question: The following code:\n```python\n{entire_buggy_code.strip()}\n```\n"
    #         f"has a bug and leads to this test failure:\n```\n{tests_output.strip()}\n```")
    # return (f"Question: The code shown below (always the updated version is displayed, "
    #         f"so if you have previously changed something, these changes will be included in the code below) "
    #         f"has a bug.\n"
    #         f"When executing its tests, the following output is produced:\n```\n{tests_output.strip()}\n```")

    return (f"Question: The code shown below (always the updated version is displayed, "
            f"so if you have previously changed something, these changes will be included in the code below) "
            f"may have a bug.\n"
            f"The output of execits tests is also displayed below (again, always the latest output after your changes)")
