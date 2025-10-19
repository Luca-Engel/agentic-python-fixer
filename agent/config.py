from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_name: str = "Qwen/Qwen3-0.6B"
    run_type: str = "local"  # options: local, openai, hf_api


@dataclass
class RuntimeConfig:
    max_iters: int = 10
    test_timeout_s: int = 10
    mem_limit_mb: int = 2048
    cpu_time_s: int = 10
    wall_time_s: int = 20
    seed: int = 0
