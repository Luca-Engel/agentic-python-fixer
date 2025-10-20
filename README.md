# 🧠 Agentic Python Fixer

An **LLM-powered automatic Python bug fixer** that uses a **ReAct (Reason + Act)** loop with **two cooperating agents** — a *Thought agent* and a *Patch agent* — to iteratively repair buggy code until all tests pass.  

This framework runs models **locally**, via **OpenAI’s API**, or via the **Hugging Face Inference API**, and executes test runs securely in a **Docker sandbox** to prevent untrusted code from escaping its environment.

---

## 📈 Results

The Jupyter notebook `notebooks/Model_Performance_Analysis.ipynb` contains detailed performance analyses across different models and dataset subsets along with visualizations and analysis of the plots.



---


## 📁 Project Structure

```text
.
├── agent/ # Core agent logic
│ ├── config.py # Model and runtime configuration
│ ├── docker_sandbox.py # Docker-based sandbox for pytest execution
│ ├── patches.py # Patch representation and application
│ ├── prompts.py # ReAct prompt templates (Thought + Patch)
│ ├── react_loop.py # The main ReAct reasoning loop
│ └── tools.py # Filesystem and execution utilities
├── eval/ # Evaluation and dataset interface
│ ├── humanevalfix_loader.py # Loads and stratifies HumanEvalFix tasks
│ ├── scorer.py # pass@1 metric computation
│ ├── evaluate.py # Runs a single repair task
│ └── task_workspace.py # Manages per-task isolated workspaces
├── docker/sandbox.Dockerfile # Secure sandbox environment definition
├── scripts/run_all.py # Main CLI entry point
├── reports/ # JSON reports from experiments
└── tests/ # Unit tests for all core components
````

---

## ⚙️ Installation

This project uses [**uv**](https://github.com/astral-sh/uv) (a fast Python package and environment manager) for reproducible dependency management.

### 1. Install `uv` (if not already installed) 
Follow the [installation guide](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set up the environment

Create a virtual environment and install dependencies:

```bash
uv sync
```

This reads from `pyproject.toml` and installs all the required packages.

---

## 🧩 Docker Sandbox Setup

The bug-fixing loop executes tests inside a **secure Docker sandbox** to safely run untrusted user code.

Before the first run, build the sandbox image:

```bash
docker build -t agentic-fixer-sandbox -f docker/sandbox.Dockerfile .
```

Ensure Docker is installed and running — otherwise, the system will raise an error indicating that the image or
daemon is missing.

---

## 🚀 Running the System

The main entry point is `scripts/run_all.py`.
You can launch it through **uv** as follows:

```bash
uv run python scripts/run_all.py \
  --run-type hf_api \
  --subset stratified_0.25 \
  --max-iters 5 \
  --timeout-secs 10 \
  --report reports/qwen1-7_hef_fix_py_sub40_00-58.json
```

### Parameters

| Flag             | Description                                                                                                                                                                                                                                                          |
| ---------------- |----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--run-type`     | Which model backend to use — options: `local`, `openai`, `hf_api`                                                                                                                                                                                                    |
| `--subset`       | Dataset subset, e.g. `all` or `stratified_<fraction>`, where <fraction> signifies what fraction of each bug type should appear in the dataset (e.g., `stratified_0.25`). To make evaluation robust, a minimum of 5 samples per bug type is enforced during sampling. |
| `--max-iters`    | Maximum number of ReAct iterations per task                                                                                                                                                                                                                          |
| `--timeout-secs` | Timeout (in seconds) for each test run                                                                                                                                                                                                                               |
| `--report`       | Output JSON report file path                                                                                                                                                                                                                                         |

### Example Backends

* **`local`** — loads a model via `transformers` (default: `Qwen/Qwen3-0.6B`)
* **`openai`** — uses the OpenAI API (requires `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`)
* **`hf_api`** — uses Hugging Face Inference API (requires `HF_TOKEN`, `HF_MODEL`, and `HF_MODEL_API_URL` in `.env`)

Example `.env` file:

```env
HF_TOKEN=<your_hf_token>
HF_MODEL=<can be found on the huggingface inference endpoint page>
HF_MODEL_API_URL=<can be found on the huggingface inference endpoint page>
OPENAI_API_KEY=<your_openai_key>
OPENAI_MODEL=gpt-4o-mini
```

---

## 🧠 ReAct Loop Overview

Each repair iteration proceeds as follows:

1. **Thought Agent**

    * Reads the latest test failures and code.
    * Suggests one minimal fix as `Thought[<action description>]`.

2. **Patch Agent**

    * Converts the Thought into a structured JSON patch:
      `Patch[{"start":12,"end":13,"nb_indents":1,"text":"return False"}]`
    * The patch fields are:
      * `start`: starting line number (1-indexed, inclusive)
      * `end`: ending line number (1-indexed, exclusive)
      * `nb_indents`: number of leading indents for the new code
      * `text`: new code to insert

3. **Tools**

    * Applies the patch, reruns tests inside Docker, and feeds results back into the loop.

The loop continues until all tests pass or `max_iters` is reached.

---

## 🧪 Testing

All tests are in the `tests/` directory.

---

## 📊 Reports

Each run outputs a JSON report containing the results for each task. Each task entry includes:
- `task_id`: unique identifier of the task
- `status`: `pass` or `fail`
- `nb_trajectory_elems`: number of ReAct iterations taken
- `latest_code`: the final repaired code (or last attempted code)

The script also prints an aggregate **pass@1** score summarizing success rate:

```
pass@1 = 32/40 = 0.800
```

---

## 🧾 License

This project is distributed under the MIT License.
Feel free to use, modify, and build upon it for research or development.

---

**Author:** *Luca Engel*

