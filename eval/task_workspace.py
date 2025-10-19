import os, tempfile, shutil, textwrap


class TaskWorkspace:
    def __init__(self, task, keep: bool = False):
        self.tmp = tempfile.mkdtemp(prefix=f"{task['task_id']}_")
        self.keep = keep
        with open(os.path.join(self.tmp, task["entry_file"]), "w", encoding="utf-8") as f:
            # f.write(task["buggy_solution"])
            f.write(task["entire_buggy_code"])
        with open(os.path.join(self.tmp, "raw_test_task.py"), "w", encoding="utf-8") as f:
            # f.write(f"from task import {task['entry_point']}\n\n")
            f.write(task["test"].strip())

        with open(os.path.join(self.tmp, "test_task.py"), "w", encoding="utf-8") as f:
            f.write(task["entire_buggy_code"] + "\n\n\n" + task["test"].strip())

    def path(self): return self.tmp

    def cleanup(self):
        if not self.keep and os.path.isdir(self.tmp):
            shutil.rmtree(self.tmp, ignore_errors=True)
