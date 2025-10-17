import json
from typing import Dict, Any

from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from agent.docker_sandbox import run_pytests_docker
from agent.prompts import get_task_header
from agent.tools import Toolset
from agent.react_loop import ReActLoop
from agent.config import ModelConfig, RuntimeConfig
from eval.humanevalfix_loader import load_tasks
from eval.task_workspace import TaskWorkspace

from dotenv import load_dotenv
import os
import openai


def make_llm(model_cfg: ModelConfig):
    """
    Create a language model callable from the given configuration.
    """
    # print("Loading model:", model_cfg.model_name)
    # tok = AutoTokenizer.from_pretrained(model_cfg.model_name)
    # model = AutoModelForCausalLM.from_pretrained(model_cfg.model_name, device_map="auto")
    # print("Model loaded.")
    # gen = pipeline(
    #     "text-generation",
    #     model=model,
    #     tokenizer=tok,
    #     return_full_text=False,
    #     temperature=model_cfg.temperature,
    #     top_p=model_cfg.top_p,
    #     top_k=model_cfg.top_k,
    #     min_p=model_cfg.min_p,
    #     max_new_tokens=model_cfg.max_new_tokens
    # )
    #
    # def _call(prompt: str) -> str:
    #     out = gen(prompt, num_return_sequences=1)[0]["generated_text"]
    #     return out

    load_dotenv()  # loads .env into environment
    api_key = os.getenv("OPENAI_API_KEY")
    env_model = os.getenv("OPENAI_MODEL")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment or .env")

    _client = OpenAI(api_key=api_key)

    def _call(prompt: str) -> str:

        resp = _client.chat.completions.create(
            model=env_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return resp.choices[0].message.content

    return _call


def run_single_task(task: Dict[str, Any], model_cfg: ModelConfig, rt_cfg: RuntimeConfig):
    ws = TaskWorkspace(task)
    try:
        tools = Toolset(workdir=ws.path(), sandbox_runner=run_pytests_docker)
        llm = make_llm(model_cfg)
        loop = ReActLoop(llm=llm, tools=tools, max_iters=rt_cfg.max_iters)
        tests_output = tools.run_pytests().output
        header = get_task_header(entire_buggy_code=task['entire_buggy_code'], tests_output=tests_output)
        res = loop.run(task_header=header)
        # Final adjudication: run tests one last time
        ok = tools.run_pytests(timeout_s=rt_cfg.test_timeout_s,
                               mem_mb=rt_cfg.mem_limit_mb,
                               cpu_time_s=rt_cfg.cpu_time_s).ok
        return {
            "task_id": task["task_id"],
            "status": "pass" if ok else "fail",
            "iters": len(res.get("trajectory", [])),
        }
    finally:
        ws.cleanup()


if __name__ == "__main__":
    tasks = load_tasks()
    tasks = tasks.select(range(1))

    model: str = "Qwen/Qwen3-0.6B"
    subset: str = "all"
    max_iters: int = 10
    timeout_secs: int = 10

    mcfg = ModelConfig(model_name=model)
    rcfg = RuntimeConfig(max_iters=max_iters, test_timeout_s=timeout_secs)
    results = []

    for t in tasks:
        ws = TaskWorkspace(t)
        tools = Toolset(workdir=ws.path(), sandbox_runner=run_pytests_docker)
        output = tools.run_pytests().output
        print(f"Test output:\n{output}")
        ws.cleanup()