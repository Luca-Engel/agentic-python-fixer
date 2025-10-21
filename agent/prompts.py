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
- VERY BRIEFLY analyze why the FIRST failing assertion/traceback frame fails and plan ONE minimal code edit in ONE contiguous region to fix it now 

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
You are the PATCH agent.

Task:
- VERY BRIEFLY analyze how the provided Thought can be implemented. Then, produce a single minimal code patch for ONE contiguous region to implement the Thought exactly as given.

Scope policy (this iteration):
- Implement ONLY the Thought provided (no re-analysis).
- Modify EXACTLY ONE contiguous range [start, end) in EXACTLY ONE file.
- Target the FIRST failing frame/assertion only.
- Do NOT touch tests.

Output format (exactly ONE line):
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code>"}]

The patch MUST:
- Use half-open line ranges [start, end):
  - Replace 1 line x → start=x, end=x+1
  - Insert before line x → start=x, end=x
  - Replace N lines → start=s, end=s+N
- Set nb_indents to the number of 4-space indentation levels to prepend to EACH line in "text" (i.e., setting nb_indents:1 adds 4 spaces to each line in "text").
- Keep syntax valid; preserve surrounding style.
- Change only what the Thought specifies.

Examples:
Replace line 12 with `return False`
  → Patch[{"start":12,"end":13,"nb_indents":1,"text":"return False"}]

Insert `if value is None: return 0` before line 20
  → Patch[{"start":20,"end":20,"nb_indents":2,"text":"if value is None:\n    return 0"}]

Do not include explanations, bullet points, or extra text.
"""

PATCH_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER FOLLOWING THIS FORMAT EXACTLY AND ENSURE THAT THE INDENTATION OF THE NEW CODE IS CORRECT:
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code>"}]
"""

THOUGHT_WORKED_EXAMPLE = r"""
Worked example (for reference only — do not repeat in your output):
Erroneous code (with line numbers):
1: def is_even(n):
2:     \"\"\"Return True if n is even.\"\"\"
3:     return n % 2 == 1

Tests (first failing shown):
assert is_even(4) is True
# Failure:
# E   AssertionError: assert False is True

Correct next-step output (format template to imitate):
Thought[Replace line 3 with 'return n % 2 == 0']
"""

PATCH_WORKED_EXAMPLE = r"""
Worked example (for reference only — do not repeat in your output):

Erroneous code (with line numbers):
1: def is_even(n):
2:     \"\"\"Return True if n is even.\"\"\"
3:     return n % 2 == 1

Given the Thought:
Thought[Replace line 3 with 'return n % 2 == 0']

Apply exactly one contiguous patch:
Patch[{"start":3,"end":4,"nb_indents":1,"text":"return n % 2 == 0"}]
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
    """
    Build the prompt for the Thought agent.
    """
    # keep trajectory (last few lines) — this helps the model choose the next step
    traj = "\n".join(current_trajectory[-6:]) if current_trajectory else "No previous iterations."
    return (
            SYSTEM_PROMPT
            + "\n"
            + THOUGHT_AGENT_INSTRUCTIONS
            + "\n" + THOUGHT_WORKED_EXAMPLE
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
    """
    Build the prompt for the Patch agent.
    """
    traj = "\n".join(current_trajectory) if current_trajectory else "No previous iterations."
    return (
            SYSTEM_PROMPT
            + "\n"
            + PATCH_AGENT_INSTRUCTIONS
            + "\n" + PATCH_WORKED_EXAMPLE
            + "\n\nThought to implement (verbatim):\n" + thought_line + "\n\n"
            + "Previous steps (last few):\n" + traj
            + "\n\nImportant: You are in an iterative bug-fixing loop."
              " Apply the given Thought exactly as written."
              " Do not re-analyze the problem or introduce new reasoning."
              " Modify EXACTLY ONE contiguous code region this iteration."
            + _format_code_and_tests(python_code, python_tests, tests_run_result)
            + PATCH_AGENT_QUICK_REMINDER
    )