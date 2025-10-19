import os
import tempfile

from agent.docker_sandbox import run_pytests_docker


def test_pytest_runs():
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "t.py"), "w") as f:
        f.write("def f():\n    return 1\n")
    with open(os.path.join(tmp, "test_t.py"), "w") as f:
        f.write("from t import f\n\ndef test_ok():\n    assert f()==1\n")
    code, out = run_pytests_docker(tmp, timeout_s=5, mem_mb=512)
    assert code == 0, out
