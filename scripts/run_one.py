import typer, json
from eval.humanevalfix_loader import load_tasks
from eval.evaluate import run_single_task
from agent.config import ModelConfig, RuntimeConfig

app = typer.Typer()


@app.command()
def main(task_id: str,
         model: str = "Qwen/Qwen3-0.6B",
         max_iters: int = 10,
         timeout_secs: int = 10):
    task = next(t for t in load_tasks(split="test") if t["task_id"] == task_id)
    res = run_single_task(task, ModelConfig(model_name=model),
                          RuntimeConfig(max_iters=max_iters, test_timeout_s=timeout_secs))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    app()
