import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer

from agent.config import ModelConfig, RuntimeConfig
from agent.langgraph_react_loop import LangGraphReActLoop
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
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        # Tokenize and move tensors to model device
        inputs = tok(text, return_tensors="pt").to(model.device)

        gen = model.generate(
            **inputs,
            max_new_tokens=30000,
            do_sample=True,
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            # min_p=0.0,
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


def _instantiate_model_hf_api(frequency_penalty=0.2, presence_penalty=0.0):
    load_dotenv()  # loads .env into environment
    api_key = os.getenv("HF_TOKEN")
    env_model = os.getenv("HF_MODEL")
    base_url = os.getenv("HF_MODEL_API_URL")

    _client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    # for message in chat_completion:
    #     print(message.choices[0].delta.content, end="")
    def _call(prompt: str) -> str:
        resp = _client.chat.completions.create(
            model=env_model,
            messages=[{"role": "user", "content": prompt}],
            seed=42
            # stream=True,
            # Thinking mode
            # temperature=0.6,
            # top_p=0.95,
            # presence_penalty=presence_penalty,
            # frequency_penalty=frequency_penalty,
            # max_tokens=30000,



            # top_k=20,
            # min_p=0,
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
    Returns a tuple (llm_thought, llm_patch)
    """
    if model_cfg.run_type == "local":
        print("Using local model.")
        return _instantiate_model_locally(model_cfg), _instantiate_model_locally(model_cfg)
    elif model_cfg.run_type == "openai":
        print("Using OpenAI model.")
        return _instantiate_model_openai(), _instantiate_model_openai()
    elif model_cfg.run_type == "hf_api":
        print("Using HuggingFace API model.")
        return _instantiate_model_hf_api(frequency_penalty=0.0, presence_penalty=0.0), _instantiate_model_hf_api(0.0, 0.0)
    else:
        raise ValueError(f"Unknown model run_type: {model_cfg.run_type}, must be one of 'local', 'openai', 'hf_api'.")


def run_single_task(task: Dict[str, Any], model_cfg: ModelConfig, rt_cfg: RuntimeConfig):
    ws = TaskWorkspace(task)
    try:
        tools = Toolset(workdir=ws.path())
        llm_thought, llm_patch = make_llm(model_cfg)
        loop = LangGraphReActLoop(llm_thought=llm_thought, llm_patch=llm_patch, tools=tools,
                             max_iters = rt_cfg.max_iters)
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
