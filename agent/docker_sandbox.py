import os
import shutil
import subprocess
import sys
from typing import Tuple, List

SANDBOX_IMAGE = os.environ.get("AF_SANDBOX_IMAGE", "agentic-fixer-sandbox")


def _ensure_docker() -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Docker not found on PATH. Please install Docker Desktop/Engine.")
    # optional: verify image present
    try:
        subprocess.run(["docker", "image", "inspect", SANDBOX_IMAGE],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"Docker image '{SANDBOX_IMAGE}' not found. Build it:\n"
            f"  docker build -t {SANDBOX_IMAGE} -f docker/sandbox.Dockerfile ."
        )


def run_pytests_docker(
        workdir: str,
        timeout_s: int = 10,
        mem_mb: int = 2048,
        cpu_quota: float = 1.0,  # logical CPUs
        extra_pytest_args: List[str] = None,
) -> Tuple[int, str]:
    """
    Execute pytest inside an isolated Docker container.

    Security hardening:
      --network none (no internet)
      --read-only + tmpfs /tmp
      --cap-drop ALL, no-new-privileges
      --pids-limit, memory limit, CPU limit
      user namespace with current host uid/gid to avoid root writes on bind mount
    """
    _ensure_docker()

    extra_pytest_args = extra_pytest_args or []
    uid = str(os.getuid()) if hasattr(os, "getuid") else "1000"
    gid = str(os.getgid()) if hasattr(os, "getgid") else "1000"

    # Resource flags
    cpu_flag = ["--cpus", str(max(0.1, float(cpu_quota)))]
    mem_flag = ["--memory", f"{mem_mb}m", "--memory-swap", f"{mem_mb}m"]
    pid_flag = ["--pids-limit", "256"]

    # Security flags
    sec_flags = [
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--ulimit", "nofile=1024:1024",
        "--ulimit", "nproc=256:256",
        "--tmpfs", "/tmp:size=64m,mode=1777",
    ]

    # Bind mount workspace at /workspace (rw)
    mount = ["-v", f"{os.path.abspath(workdir)}:/workspace:rw"]
    user = ["-u", f"{uid}:{gid}"]
    envs = ["-e", "PYTHONHASHSEED=0"]

    cmd = [
        "docker", "run", "--rm",
        *cpu_flag, *mem_flag, *pid_flag, *sec_flags,
        *mount, *user, *envs,
        "-w", "/workspace",
        SANDBOX_IMAGE,
        "python", "-m", "pytest", "-q", "--disable-warnings",
        "--maxfail=1",  # faster feedback
        "--timeout", str(timeout_s),
        *extra_pytest_args,
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s + 2,  # small cushion for docker runtime
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as e:
        # If Docker wrapper times out (unlikely due to pytest-timeout), report it
        out = (e.stdout or "") + "\n[agent] Container timed out."
        return 124, out
