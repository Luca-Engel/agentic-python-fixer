from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_name: str = "Qwen/Qwen3-0.6B"
    device: str = "cpu"
    dtype: str = "auto"
    temperature: float = 0.7
    top_p: float = 0.8
    do_sample: bool = True
    top_k: int = 20
    min_p: float = 0.0
    max_new_tokens: int = 32768
    enable_thinking: bool = False #True
    add_generation_prompt: bool = True
    tokenize: bool = False


@dataclass
class RuntimeConfig:
    max_iters: int = 10
    test_timeout_s: int = 10
    mem_limit_mb: int = 2048
    cpu_time_s: int = 10
    wall_time_s: int = 20
    seed: int = 0
