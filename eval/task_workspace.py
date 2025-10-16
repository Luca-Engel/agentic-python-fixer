import os, tempfile, shutil, textwrap


class TaskWorkspace:
    def __init__(self, task, keep: bool = False):
        self.tmp = tempfile.mkdtemp(prefix=f"{task['task_id']}_")
        self.keep = keep
        with open(os.path.join(self.tmp, task["entry_file"]), "w", encoding="utf-8") as f:
            f.write(task["buggy_solution"])
        with open(os.path.join(self.tmp, "test_task.py"), "w", encoding="utf-8") as f:
            f.write(task["test"])

    def path(self): return self.tmp

    def cleanup(self):
        if not self.keep and os.path.isdir(self.tmp):
            shutil.rmtree(self.tmp, ignore_errors=True)
