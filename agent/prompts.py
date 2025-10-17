SYSTEM_PROMPT = """You are a Python bug-fixing assistant.
You will iteratively: (1) read files/tests and failure traces, (2) propose small patches,
(3) re-run tests, (4) stop when tests pass. Keep changes minimal and safe."""

REACT_INSTRUCTIONS = """
Use this ReAct format:

Thought: brief reasoning on the failures and what to do next.
Action: ActionName[ActionInput]
Observation: (tool output filled in by the system)

Repeat until tests pass, then call Finish[{"message": "the fixed code"}] with a brief summary.

Allowed actions:
- Patch[{"start": <int>, "end": <int>, "text": "<new code>"}]
        (use replace patches only; "start" and "end" are character offsets
        in the file; "text" is the new content with which to replace that section)
- RunPytests[]
- Finish[<brief summary of the fix>]
"""

FEW_SHOT = r"""
# Example
Question: The following code: <code omitted for brevity>
has a bug and leads to this test failure: <failure trace omitted for brevity>
Thought: The test says TypeError due to None. Add default return value.
Action: Patch[{"type":"replace","start":12,"end":18,"text":"    return 0\n"}]
Observation: Patch applied.
Thought: Re-run tests.
Action: RunPytests[]
Observation: All tests passed.
Thought: Done.
Action: Finish[]
"""
