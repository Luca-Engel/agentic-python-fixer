from datasets import load_dataset
import math, random
from collections import defaultdict


def add_file_names_to_row(row):
    return {
        "task_id": row["task_id"].replace("/", "_"),
        "entire_buggy_code": f"""{row["declaration"]}    '''\n{row["docstring"]}\n    '''\n{row["buggy_solution"]}""",
        "entry_file": "task.py",
        "raw_test_file": "raw_test_task.py",
        "test_file": "test_task.py",
    }


def load_tasks(ds_id: str = "bigcode/humanevalpack", lang: str = "python", split: str = "test"):
    columns = ["task_id", "declaration", "entire_buggy_code", "test", "entry_point", "bug_type", "entry_file", "raw_test_file", "test_file"]
    ds = load_dataset(ds_id, name=lang, split=split)
    ds = ds.map(add_file_names_to_row, desc="normalize")
    print("Original columns:", ds.column_names)

    ds = ds.select_columns(columns)

    return ds


def stratified_sample(ds, percent: float = 0.25, min_per_class: int = 5, seed: int = 42):
    """
    Stratified sampling by bug_type. Enforces at least min_per_class samples per class,
    but never includes the same task twice.
    """
    if not (0.0 <= percent <= 1.0):
        raise ValueError("percent must be between 0.0 and 1.0")

    rng = random.Random(seed)
    tasks_ = list(ds)

    by_type = defaultdict(list)
    for t in tasks_:
        by_type[t["bug_type"]].append(t)

    sampled = []
    for bug_type_, ts in by_type.items():
        if not ts:
            continue
        n_desired = max(min_per_class, math.ceil(len(ts) * percent))
        # Never select more than available unique tasks to avoid duplicates
        n_selected = min(n_desired, len(ts))
        sampled.extend(rng.sample(ts, n_selected))

    return sampled


if __name__ == "__main__":
    from collections import Counter

    tasks = load_tasks()
    # print("Dataset fields:", tasks.column_names)
    # print(f"Loaded {len(tasks)} tasks, example:")
    # first_task = tasks[0]
    # print("first task buggy code:")
    # print(first_task["entire_buggy_code"])

    counts = Counter(tasks["bug_type"])
    print("\nBug type counts:")
    for bug_type, cnt in counts.most_common():
        print(f"  {bug_type}: {cnt}")
    print(f"\nTotal tasks counted: {sum(counts.values())}")

    sampled_tasks = stratified_sample(tasks, percent=0.2, min_per_class=5, seed=42)
    sampled_counts = Counter(t["bug_type"] for t in sampled_tasks)
    print("\nSampled bug type counts:")
    for bug_type, cnt in sampled_counts.most_common():
        print(f"  {bug_type}: {cnt}")
    print(f"\nTotal sampled tasks: {len(sampled_tasks)}")
