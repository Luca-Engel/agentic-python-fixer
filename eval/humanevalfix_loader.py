from datasets import load_dataset


def add_file_names_to_row(row):
    return {
        "task_id": row["task_id"].replace("/", "_"),
        "entire_buggy_code": f"""{row["declaration"]}    '''\n{row["docstring"]}\n    '''\n{row["buggy_solution"]}""",
        # "entire_buggy_code": f"""{row["declaration"]}{row["canonical_solution"]}""",
        "entry_file": "task.py",
        "test_file": "test_task.py",
    }


def load_tasks(ds_id: str = "bigcode/humanevalpack", lang: str = "python", split: str = "test"):
    columns = ["task_id", "declaration", "entire_buggy_code", "test", "entry_point", "bug_type", "entry_file", "test_file"]
    # columns = ["task_id", "declaration", "buggy_solution", "entire_buggy_code", "test", "entry_point", "bug_type", "entry_file", "test_file"]
    ds = load_dataset(ds_id, name=lang, split=split)
    ds = ds.map(add_file_names_to_row, desc="normalize")
    print("Original columns:", ds.column_names)

    ds = ds.select_columns(columns)

    return ds


if __name__ == "__main__":
    tasks = load_tasks()
    print("Dataset fields:", tasks.column_names)
    print(f"Loaded {len(tasks)} tasks, example:")
    first_task = tasks[0]
    print("first task buggy code:")
    print(first_task["entire_buggy_code"])
