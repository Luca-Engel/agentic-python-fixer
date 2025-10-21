import os
import tempfile

from agent.docker_sandbox import run_pytests_docker


def test_pytest_runs():
    # Note that docker needs to be running for this test to pass
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "t.py"), "w") as f:
        f.write("def f():\n    return 1\n")
    with open(os.path.join(tmp, "test_t.py"), "w") as f:
        f.write("from t import f\n\ndef check():\n    assert f()==1\n\ncheck()\n")
    code, out = run_pytests_docker(tmp, timeout_s=5, mem_mb=512)
    assert code == 5, out
