import os
from dataclasses import dataclass

from agent.docker_sandbox import run_pytests_docker
from agent.patches import SpanPatch, apply_span_patch


@dataclass
class ToolResult:
    ok: bool
    output: str


def get_text_with_indents(nb_indents: int, text: str) -> str:
    """
    Adjust the text by removing common leading spaces and adding specified indents.
    """
    lines = text.splitlines()
    if lines:
        first_line = lines[0]
    else:
        first_line = ""
        lines = [""]

    leading = len(first_line) - len(first_line.lstrip()) if first_line else 0
    processed_lines = []
    for line in lines:
        if leading > 0 and line.startswith(' ' * leading):
            processed_lines.append(line[leading:])
        else:
            processed_lines.append(line)

    indent = "    " * nb_indents
    text_with_indents = "\n".join(indent + line for line in processed_lines) + "\n"
    return text_with_indents


class Toolset:
    def __init__(self, workdir: str):
        self.workdir = workdir

    def open_file(self, path: str) -> ToolResult:
        """
        Open a file in the workspace and return its contents.
        """
        p = os.path.join(self.workdir, path)
        if not os.path.isfile(p):
            return ToolResult(False, f"File not found: {path}")
        return ToolResult(True, open(p, "r", encoding="utf-8").read())

    def write_file(self, start: int, end: int, nb_indents: int, text: str) -> ToolResult:
        """
        Write a patch to task.py and update test_task.py accordingly.
        """
        p = os.path.join(self.workdir, "task.py")
        src = open(p, "r", encoding="utf-8").read().strip()

        text_with_indents = get_text_with_indents(nb_indents, text)

        sp = SpanPatch(path=p, start=start, end=end, text=text_with_indents)
        dst = apply_span_patch(src, sp)

        with open(p, "w", encoding="utf-8") as f:
            f.write(dst)

        # update test_task.py
        test_content_p = os.path.join(self.workdir, "raw_test_task.py")
        with open(test_content_p, "r", encoding="utf-8") as f:
            test_content = f.read()

        test_p = os.path.join(self.workdir, "test_task.py")
        with open(test_p, "w", encoding="utf-8") as f:
            f.write(dst + "\n\n\n" + test_content)

        return ToolResult(True, "Wrote patch.")

    def run_pytests(self, timeout_s: int = 10, mem_mb: int = 2048):
        """
        Run pytest in a Docker sandbox and return the result.
        """
        code, out = run_pytests_docker(
            workdir=self.workdir,
            timeout_s=timeout_s,
            mem_mb=mem_mb,
            cpu_quota=1.0,  # adjust via config if you want fractional CPUs
        )

        # since it is not actual pytests we run, treat exit code 5 (no tests collected) as success
        # Failure means that assetions failed and then the exit code is not 5
        return ToolResult(code == 5, out)