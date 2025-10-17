import os, re, glob, json
from dataclasses import dataclass
from .patches import SpanPatch, apply_span_patch
from .docker_sandbox import run_pytests_docker


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

    def write_file(self, start: int, end: int, text: str) -> ToolResult:
        p = os.path.join(self.workdir, "task.py")
        src = open(p, "r", encoding="utf-8").read()
        # if patch.get("type") == "replace":
        sp = SpanPatch(path=p, start=start, end=end, text=text)
        dst = apply_span_patch(src, sp)
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
        return ToolResult(code == 0, out)

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
