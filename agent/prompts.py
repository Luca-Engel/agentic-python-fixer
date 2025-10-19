SYSTEM_PROMPT = """You are a Python bug-fixing assistant.

Goal: make the provided code pass ALL given tests. The tests are the single source of truth.

Rules (must follow):
- Edit ONLY the main code (never the tests).
- Make ONE minimal change per iteration.
- Touch ONE contiguous region in ONE file.
- Target the FIRST failing traceback frame / assertion only.
- Line numbers in code are 1-based. Ranges are half-open [start, end).
- Output MUST follow the requested JSON format exactly (valid JSON on a single line).
"""

THOUGHT_AGENT_INSTRUCTIONS = r"""
You are the THOUGHT agent.

Task:
- VERY BRIEFLY infer why the FIRST failing assertion/traceback frame fails and plan ONE minimal code edit in ONE contiguous region to fix it now.

Scope policy (this iteration):
- Address ONLY the first failing frame.
- Plan exactly ONE minimal edit (insert OR replace OR delete).
- Specify exact line numbers (1-based). Use [start,end) semantics for later patching.

Output format (exactly ONE line):
Thought[<one brief sentence describing the next minimal code change>]

The sentence MUST:
- State the action (Insert/Replace/Delete),
- Give the exact line number(s),
- Include the precise code intent or new statement.

Examples:
- Thought[Replace line 42 with 'return False if value is None else True']
- Thought[Insert 'if value is None:\n    return 0' before line 20 to handle None input]

Do not include explanations, bullet points, or extra text.
"""

THOUGHT_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER FOLLOWING THIS FORMAT EXACTLY:
Thought[<single brief sentence describing the next minimal change>]
"""

PATCH_AGENT_INSTRUCTIONS = r"""
You now implement the Thought as a precise, minimal code patch.

First, VERY BRIEFLY reason about how to translate the Thought into a Patch.
Then, output EXACTLY ONE LINE in this strict JSON-like format:
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code>"}]

Rules:
- Half-open range [start, end):
    - Replace 1 line x: start=x, end=x+1
    - Insert before x: start=x, end=x
    - Replace N lines: start=s, end=s+N
- nb_indents = number of 4-space indentation levels to apply uniformly to every line in "text".
- Preserve correct syntax, indentation, and spacing.
- Modify EXACTLY ONE contiguous range [start, end) in EXACTLY ONE file per iteration.
- If the Thought implies multiple regions, implement ONLY the first region and stop.
- Never modify or refer to the tests.

Examples:
Replace line 12 with `return False`
  → Patch[{"start":12,"end":13,"nb_indents":1,"text":"return False"}]

Insert `if value is None: return 0` before line 20
  → Patch[{"start":20,"end":20,"nb_indents":2,"text":"if value is None:\n    return 0"}]

End your output with the Patch[...] line only — no commentary.
"""

PATCH_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER FOLLOWING THIS FORMAT EXACTLY AND ENSURE THAT THE INDENTATION OF THE NEW CODE IS CORRECT:
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code>"}]
"""


def _format_code_and_tests(python_code: str, python_tests: str, tests_run_result: str) -> str:
    python_code_lines = python_code.splitlines()
    numbered_code = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(python_code_lines))
    return (
        "\n\n=== CURRENT CODE (with line numbers) ===\n"
        f"```python\n{numbered_code}\n```"
        "\n\n=== TEST SUITE ===\n"
        f"```python\n{python_tests}\n```"
        f"\n\n=== TEST RESULTS ==={tests_run_result}"
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
            + "\n\nYou are the THOUGHT agent."
            + THOUGHT_AGENT_INSTRUCTIONS
            + "\n\nPrevious steps (last few):\n" + traj
            + "\n\nImportant: You are continuing an iterative repair loop."
              " Use insights from previous steps but DO NOT repeat prior failed edits."
              " Base your reasoning only on the latest test failures and current code."
              " Scope for this iteration: change only ONE contiguous code region and target the earliest/first failing assertion or traceback frame."
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
            + "\n\nImportant: You are in an iterative bug-fixing loop."
              " Apply the given Thought exactly as written."
              " Do not re-analyze the problem or introduce new reasoning."
              " Modify EXACTLY ONE contiguous code region this iteration."
            + _format_code_and_tests(python_code, python_tests, tests_run_result)
            + PATCH_AGENT_QUICK_REMINDER
    )