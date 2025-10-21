import datetime
import json
import os
from typing import Literal

import typer
from tqdm import tqdm

from agent.config import ModelConfig, RuntimeConfig
from eval.evaluate import run_single_task
from eval.humanevalfix_loader import load_tasks, stratified_sample
from eval.scorer import pass_at_1

app = typer.Typer()


@app.command()
def main(run_type: str = "local", # one of ["local", "openai", "hf_api"]
         subset: str = "all",
         max_iters: int = 10,
         timeout_secs: int = 10,
         report: str = "reports/hef_py_report.json"):
    """
    Run all HumanevalFix tasks with the specified model and configuration.
    """
    if run_type not in ["local", "openai", "hf_api"]:
        raise ValueError(f"Unknown model: {run_type}, must be one of 'local', 'openai', 'hf_api'.")
    run_type_to_name = {
        "local": "Qwen/Qwen3-0.6B",
        "openai": "gpt-4o mini",
        "hf_api": "Qwen/Qwen3-1.7B"
    }
    model_name = run_type_to_name[run_type]

    tasks = load_tasks()
    if subset.startswith("stratified"):
        fraction = float(subset.split("0")[1]) if "_" in subset else 0.2
        print(f"Using stratified sampling with fraction={fraction}")
        tasks = stratified_sample(tasks, percent=fraction, min_per_class=5, seed=42)

    mcfg = ModelConfig(model_name=model_name, run_type=run_type)
    rcfg = RuntimeConfig(max_iters=max_iters, test_timeout_s=timeout_secs)
    results = []

    for i, t in enumerate(tqdm(tasks, desc="Running tasks"), start=1):
        results.append(run_single_task(t, mcfg, rcfg))
        with open(report, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    pass_at_1_score, nb_passed, nb_total = pass_at_1(results)
    print(f"pass@1 = {nb_passed}/{len(results)} = {pass_at_1_score:.3f}")

    save_run_to_benchmark(max_iters, model_name, nb_passed, nb_total, pass_at_1_score, report, run_type, subset,
                          timeout_secs)


def save_run_to_benchmark(max_iters: int, model_name: str, nb_passed: int | Literal[0], nb_total: int,
                          pass_at_1_score: float, report: str, run_type: Literal["local", "openai", "hf_api"],
                          subset: str, timeout_secs: int):
    bench_file = "benchmark/benchmark_results.json"
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "config": {
            "run_type": run_type,
            "subset": subset,
            "max_iters": max_iters,
            "timeout_secs": timeout_secs,
            "model_name": model_name,
            "report": report,
        },
        "summary": {
            "pass_at_1": pass_at_1_score,
            "nb_passed": nb_passed,
            "nb_total": nb_total,
        },
    }

    os.makedirs(os.path.dirname(bench_file), exist_ok=True)

    try:
        with open(bench_file, "r", encoding="utf-8") as bf:
            existing = json.load(bf)
            if existing is None:
                existing = []
            elif not isinstance(existing, list):
                existing = [existing]
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    existing.append(entry)

    with open(bench_file, "w", encoding="utf-8") as bf:
        json.dump(existing, bf, indent=2)


if __name__ == "__main__":
    app()
