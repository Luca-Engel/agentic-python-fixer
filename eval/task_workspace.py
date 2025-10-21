import os
import shutil
import tempfile


class TaskWorkspace:
    """
    Create a temporary workspace for a given task.
    Writes the buggy code to the specified entry file and the test code to test_task.py.
    """
    def __init__(self, task, keep: bool = False):
        self.tmp = tempfile.mkdtemp(prefix=f"{task['task_id']}_")
        self.keep = keep
        with open(os.path.join(self.tmp, task["entry_file"]), "w", encoding="utf-8") as f:
            f.write(task["entire_buggy_code"])
        with open(os.path.join(self.tmp, "raw_test_task.py"), "w", encoding="utf-8") as f:
            f.write(task["test"].strip())

        with open(os.path.join(self.tmp, "test_task.py"), "w", encoding="utf-8") as f:
            f.write(task["entire_buggy_code"] + "\n\n\n" + task["test"].strip())

    def path(self):
        """
        Get the path to the temporary workspace.
        """
        return self.tmp

    def cleanup(self):
        """
        Clean up the temporary workspace unless keep is True.
        """
        if not self.keep and os.path.isdir(self.tmp):
            shutil.rmtree(self.tmp, ignore_errors=True)
