import os, re, glob, json
from dataclasses import dataclass

from agent.patches import SpanPatch, apply_span_patch
from agent.docker_sandbox import run_pytests_docker
from eval.task_workspace import TaskWorkspace


@dataclass
class ToolResult:
    ok: bool
    output: str


class Toolset:
    def __init__(self, workdir: str, sandbox_runner):
        self.workdir = workdir
        self.sandbox_runner = sandbox_runner

    def open_file(self, path: str) -> ToolResult:
        p = os.path.join(self.workdir, path)
        if not os.path.isfile(p):
            return ToolResult(False, f"File not found: {path}")
        return ToolResult(True, open(p, "r", encoding="utf-8").read())

    def write_file(self, start: int, end: int, nb_indents: int, text: str) -> ToolResult:
    # def write_file(self, text: str) -> ToolResult:
        p = os.path.join(self.workdir, "task.py")
        src = open(p, "r", encoding="utf-8").read().strip()

        print("3.1 Before patch:")
        print(src)
        text_with_indents = "    " * nb_indents + text.strip() + "\n"
        sp = SpanPatch(path=p, start=start, end=end, text=text_with_indents)
        dst = apply_span_patch(src, sp)
        print(f"3.2 After patch (start={start}, end={end}):")
        print(dst)
        print("----------------")
        # dst = text  # replace entire file


        with open(p, "w", encoding="utf-8") as f:
            f.write(dst)
        return ToolResult(True, "Wrote patch.")

    def run_pytests(self, timeout_s: int = 10, mem_mb: int = 2048, cpu_time_s: int = 10):
        # cpu_time_s is not used directly; we expose 'cpu_quota' via cpus param
        code, out = run_pytests_docker(
            workdir=self.workdir,
            timeout_s=timeout_s,
            mem_mb=mem_mb,
            cpu_quota=1.0,  # adjust via config if you want fractional CPUs
        )
        # since it is not actual pytests we run, treat exit code 5 (no tests collected) as success
        # Failure means that assetions failed and then the exit code is not 5
        return ToolResult(code == 5, out)

    def search_repo(self, query: str, max_hits: int = 20) -> ToolResult:
        hits = []
        for path in glob.glob(os.path.join(self.workdir, "**/*.py"), recursive=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if query in line:
                            hits.append(f"{os.path.relpath(path, self.workdir)}:{i}:{line.strip()}")
                            if len(hits) >= max_hits:
                                break
            except Exception:
                pass
        return ToolResult(True, "\n".join(hits) or "(no hits)")



# if __name__ == "__main__":
#     src = """from typing import List
#
#
# def has_close_elements(numbers: List[float], threshold: float) -> bool:
#     for idx, elem in enumerate(numbers):
#         for idx2, elem2 in enumerate(numbers):
#             if idx != idx2:
#                 distance = elem - elem2
#                 if distance < threshold:
#                     return True
#
#     return False"""
#
#     text = """                distance = abs(elem - elem2)"""
#     start = 8
#     end = 9
#
#     sp = SpanPatch(path="p", start=start, end=end, text=text)
#     dst = apply_span_patch(src, sp)
#
#     print("after patch:")
#     print(dst)


if __name__ == "__main__":
    correct_code = """
from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = abs(elem - elem2)
                if distance < threshold:
                    return True
 
    return False
"""

    buggy_code = """
from typing import List


def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(numbers):
            if idx != idx2:
                distance = elem - elem2
                if distance < threshold:
                    return True
 
    return False
"""

    test_code = """
def check(has_close_elements):
    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True
    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False
    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True
    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False
    assert has_close_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True
    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True
    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False

check(has_close_elements)

    """

    task = {
        "task_id": "id_123",
        "entry_file": "task.py",
        "entry_point": "has_close_elements",
        "entire_buggy_code": buggy_code, # correct_code,
        "test": test_code,
    }

    ws = TaskWorkspace(task)
    tools = Toolset(workdir=ws.path(), sandbox_runner=run_pytests_docker)

    # code, output = run_pytests_docker(
    #     workdir=tools.workdir
    # )

    tool_res = tools.run_pytests()
    print("ToolResult:", tool_res)

    # print("Exit code:", code)
    # print("Output:\n", output)
