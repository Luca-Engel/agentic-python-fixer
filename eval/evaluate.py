import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer

from agent.config import ModelConfig, RuntimeConfig
from agent.react_loop import ReActLoop
from agent.tools import Toolset
from eval.task_workspace import TaskWorkspace


def _instantiate_model_locally(model_cfg: ModelConfig):
    print("Loading model:", model_cfg.model_name)
    tok = AutoTokenizer.from_pretrained(model_cfg.model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_cfg.model_name,
        dtype="auto",
        device_map="auto",
    )
    print("Model loaded.")

    def _call(prompt: str) -> str:
        """
        Generate a completion from the local model.
        """
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(
            messages,
            tokenize=model_cfg.tokenize,
            add_generation_prompt=model_cfg.add_generation_prompt,
            enable_thinking=model_cfg.enable_thinking,
        )

        # Tokenize and move tensors to model device
        inputs = tok(text, return_tensors="pt").to(model.device)

        gen = model.generate(
            **inputs,
            max_new_tokens=model_cfg.max_new_tokens,
            do_sample=model_cfg.do_sample,
            temperature=model_cfg.temperature,
            top_p=model_cfg.top_p,
            top_k=model_cfg.top_k,
        )

        # Extract only the generated portion and decode
        output_ids = gen[0][len(inputs.input_ids[0]):].tolist()
        content = tok.decode(output_ids, skip_special_tokens=True).strip("\n")
        return content

    return _call


def _instantiate_model_openai():
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


def _instantiate_model_hf_api():
    load_dotenv()  # loads .env into environment
    api_key = os.getenv("HF_TOKEN")
    env_model = os.getenv("HF_MODEL")

    _client = OpenAI(
        base_url="https://h9yo77jwpffhw2sb.us-east4.gcp.endpoints.huggingface.cloud/v1/",
        api_key=api_key
    )

    # for message in chat_completion:
    #     print(message.choices[0].delta.content, end="")
    def _call(prompt: str) -> str:
        resp = _client.chat.completions.create(
            model=env_model,
            messages=[{"role": "user", "content": prompt}],
            # stream=True,
            # Thinking mode
            temperature=0.6,
            top_p=0.95,
            # top_k=20,
            # min_p=0,
            max_tokens=5000,
            seed=42
            # Non-thinking mode
            # temperature=0.7,
            # top_p=0.8,
            # top_k=20,
            # min_p=0,
            # max_tokens=5000,
            # seed=42
        )

        content = resp.choices[0].message.content
        print("len generated content:", len(content.split()))

        return content  #resp.choices[0].message.content

    return _call


def make_llm(model_cfg: ModelConfig):
    """
    Create a language model callable from the given configuration.
    """
    # return _instantiate_model_locally(model_cfg)
    # return _instantiate_model_openai()
    return _instantiate_model_hf_api()


def run_single_task(task: Dict[str, Any], model_cfg: ModelConfig, rt_cfg: RuntimeConfig):
    ws = TaskWorkspace(task)
    try:
        tools = Toolset(workdir=ws.path())
        loop = ReActLoop(llm_thought=make_llm(model_cfg), llm_patch=make_llm(model_cfg), tools=tools,
                         max_iters=rt_cfg.max_iters)
        res = loop.run()

        # Finally, run the tests to see if code passes
        ok = tools.run_pytests(timeout_s=rt_cfg.test_timeout_s,
                               mem_mb=rt_cfg.mem_limit_mb).ok
        return {
            "task_id": task["task_id"],
            "status": "pass" if ok else "fail",
            "nb_trajectory_elems": len(res.get("trajectory", [])),
            "latest_code": tools.open_file("task.py").output.strip(),
        }
    finally:
        ws.cleanup()
