from datasets import load_dataset


def add_file_names_to_row(row):
    row['task_id'] = row['task_id'].replace('/', '_')  # Replace '/' with '_' to avoid path issues
    row["entry_file"] = "task.py"
    row["test_file"] = "test_task.py"

    return row


def load_tasks(ds_id: str = "bigcode/humanevalpack", lang: str = "python", split: str = "test"):
    columns = ["task_id", "buggy_solution", "test", "entry_point", "bug_type", "entry_file", "test_file"]
    ds = load_dataset(ds_id, name=lang, split=split).map(add_file_names_to_row, desc="normalize")

    ds = ds.select_columns(columns)

    return ds


if __name__ == "__main__":
    tasks = load_tasks()
    print("Dataset fields:", tasks.column_names)
    print(f"Loaded {len(tasks)} tasks, example:")
    print(tasks[0])
