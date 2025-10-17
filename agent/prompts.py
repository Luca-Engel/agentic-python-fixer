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
        (use replace patches only; "start" and "end" are the line offsets in the file (0-based), 
        i.e., "start": 0 and "end": 0 means that "text" is inserted before the first line while "start": 0 and "end": 1 means that the second line is replaced by "text";
        "text" is the new content with which to replace that section)
- RunPytests[]
- Finish[<brief summary of the fix>]

Examples — valid:
Thought: The failing test shows an IndexError; adjust bounds.
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
Question: The following code: <code omitted for brevity>
has a bug and leads to this test failure: <failure trace omitted for brevity>
Thought: The test says TypeError due to None. Add default return value.
Action: Patch[{"type":"replace","start":12,"end":12,"text":"    return 0\n"}]
Observation: Patch applied.
Thought: Re-run tests.
Action: RunPytests[]
Observation: All tests passed.
Thought: Done.
Action: Finish[]
"""

def get_task_header(entire_buggy_code: str, tests_output: str) -> str:
    return (f"Question: The following code:\n```python\n{entire_buggy_code.strip()}\n```\n"
            f"has a bug and leads to this test failure:\n```\n{tests_output.strip()}\n```")
