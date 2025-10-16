import json
import random
import typer
from tqdm import tqdm

from agent.config import ModelConfig, RuntimeConfig
from eval.evaluate import run_single_task
from eval.humanevalfix_loader import load_tasks

app = typer.Typer()


@app.command()
def main(model: str = "Qwen/Qwen3-0.6B",
         subset: str = "all",
         max_iters: int = 10,
         timeout_secs: int = 10,
         report: str = "reports/hef_py_report.json"):
    tasks = load_tasks()
    if subset.startswith("stratified"):
        # TODO: add stratified sampling by bug_type
        tasks = tasks.select(range(10))

    mcfg = ModelConfig(model_name=model)
    rcfg = RuntimeConfig(max_iters=max_iters, test_timeout_s=timeout_secs)
    results = []

    for t in tqdm(tasks, desc="Running tasks"):
        results.append(run_single_task(t, mcfg, rcfg))
    with open(report, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    passed = sum(r["status"] == "pass" for r in results)
    print(f"pass@1 = {passed}/{len(results)} = {passed / len(results):.3f}")


if __name__ == "__main__":
    app()
