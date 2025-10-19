SYSTEM_PROMPT = """You are a Python bug-fixing assistant.
You will iteratively: (1) analyze code/tests and failure traces, (2) propose small patches,
(3) re-run tests, (4) stop when tests pass. Keep changes minimal and safe.

NOTE THAT THE TESTS ARE THE ORACLE: YOUR GOAL IS TO MAKE ALL TESTS PASS. ONLY MAKE CHANGES TO THE CODE, NOT THE TESTS.
"""


THOUGHT_AGENT_INSTRUCTIONS = r"""
Please first BRIEFLY reason about what your task is, then follow this strict output format — EXACTLY ONE LINE:
Thought[<single brief sentence describing the next minimal change>]

The explanation should contain what changes should be made and if a statement should be inserted at a given line or replace an existing line.
MAKE SURE TO FOLLOW THE FORMAT EXACTLY AND END YOUR OUTPUT WITH THE Thought[...] LINE.
"""

THOUGHT_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER FOLLOWING THIS FORMAT EXACTLY:
Thought[<single brief sentence describing the next minimal change>]
"""

PATCH_AGENT_INSTRUCTIONS = r"""
Please first BRIEFLY reason about what your task is, then follow this strict output format — EXACTLY ONE LINE:
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code with newlines as needed>"}]

CRITICAL RULES (memorize before output):
- The range is half-open: it replaces/affects lines in [start, end).
- Therefore:
  • To REPLACE exactly 1 line x: start = x, end = x+1. (Never set end == start here.)
  • To INSERT a new line BEFORE line x: start = x, end = x. (Insertion has end == start.)
  • To REPLACE N lines starting at s: start = s, end = s+N.
- Ensure "text" indentation matches surrounding code. Use nb_indents = number of 4-space levels to apply to every line in "text".
- `text` is the new content (may contain only one line) that will replace the range.

EXAMPLES:
Thought: "Replace line 16 with 'a = b + c'"
→ Patch[{"start":16,"end":17,"nb_indents":4,"text":"a = b + c"}]

Thought: "Insert 'return False' before line 20"
→ Patch[{"start":20,"end":20,"nb_indents":1,"text":"return False"}]


MAKE SURE TO FOLLOW THE FORMAT EXACTLY AND END YOUR OUTPUT WITH THE Patch[...] LINE.
"""

PATCH_AGENT_QUICK_REMINDER = r"""
REMEMBER TO FINISH YOUR ANSWER FOLLOWING THIS FORMAT EXACTLY AND ENSURE THAT THE INDENTATION OF THE NEW CODE IS CORRECT:
Patch[{"start":<int>,"end":<int>,"nb_indents":<int>,"text":"<new code with newlines as needed>"}]
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
            + "\n\nYou are the THOUGHT agent."
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