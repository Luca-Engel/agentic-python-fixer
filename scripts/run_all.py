import json

import typer
from tqdm import tqdm

from agent.config import ModelConfig, RuntimeConfig
from eval.evaluate import run_single_task
from eval.humanevalfix_loader import load_tasks, stratified_sample
from eval.scorer import pass_at_1

app = typer.Typer()


@app.command()
def main(model: str = "Qwen/Qwen3-0.6B",
         subset: str = "all",
         max_iters: int = 10,
         timeout_secs: int = 10,
         report: str = "reports/hef_py_report.json"):
    tasks = load_tasks()
    if subset.startswith("stratified"):
        fraction = float(subset.split("0")[1]) if "-" in subset else 0.2
        print(f"Using stratified sampling with fraction={fraction}")
        # TODO: add stratified sampling by bug_type
        # tasks = tasks.select(range(10))
        tasks = stratified_sample(tasks, percent=fraction, min_per_class=5, seed=42)

    mcfg = ModelConfig(model_name=model)
    rcfg = RuntimeConfig(max_iters=max_iters, test_timeout_s=timeout_secs)
    results = []

    for i, t in enumerate(tqdm(tasks, desc="Running tasks"), start=1):
        print(f"=== Running task {i}/{len(tasks)}: {t['task_id']} ===")
        results.append(run_single_task(t, mcfg, rcfg))
        with open(report, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    pass_at_1_score, nb_passed, nb_total = pass_at_1(results)
    print(f"pass@1 = {nb_passed}/{len(results)} = {pass_at_1_score:.3f}")


if __name__ == "__main__":
    app()
