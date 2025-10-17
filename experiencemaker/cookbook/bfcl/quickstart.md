# BFCL Experiment Quick Start Guide

This guide helps you quickly set up and run BFCL experiments with ExperienceMaker integration.

## Env Setup

### 1. BFCL installation

#### clone the repository
```bash
git clone https://github.com/ShishirPatil/gorilla.git
```

#### Change directory to the `berkeley-function-call-leaderboard`
```bash
cd gorilla/berkeley-function-call-leaderboard
```

#### Install the package in editable mode
```bash
conda create -n bfcl-env python==3.12
conda activate bfcl-env
pip install -e .
pip install loguru
```

#### Move the dataset to the data folder under bfcl
```bash
cp -r bfcl_eval/data {/path/to/bfcl/data}
```

**Note**: The original BFCL data is designed as a benchmark dataset and does not have a train/validation split, you can use ``split_into_trainval.py`` to split JSONL file into train and validation sets.

### 2. Collect agent trajectories on training data set

Run the main experiment script to collect agent trajectories on training data set without experience(`use_experience=False`):

```bash
python run_bfcl.py
```

**Note**: 
- `max_workers`: Number of parallel workers (default: `4`)
- `num_runs`: Number of times each task is repeated (default: `4`)
- `model_name`: LLM model name (default: `qwen3-8b`)
- `enable_thinking`: Control the model's thinking mode (default: `False`)
- `data_path`: Path to the training dataset (default: `./data/multiturn_data_base_train.jsonl`)
- `answer_path`: Path to the possible answer, which are used to evaluate the model's output function (default: `./data/possible_answer`)
- Results are automatically saved to `./exp_result/{model_name}/{no_think/with_think}` directory

### 3. Start ExperienceMaker Service and Init the Experience Pool

After collecting trajectories, Launch the ExperienceMaker service to enable experience library functionality:

```bash
# Go back to the project root
cd ../..

experiencemaker \
  http_service.port=8001 \
  llm.default.model_name=qwen-max-2025-01-25 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

and then init the experience pool:

```bash
python init_exp_pool.py
```

**Configuration options in `init_exp_pool.py`:**
- `jsonl_file`: Path to the collloaded trajectories
- `service_url`: Experience maker service URL (default: `http://localhost:8001`)
- `workspace_id`: Workspace ID for the experience (default: `bfcl_v1`)
- `n_threads`: Number of threads for processing (default: `4`)
- `output_file`: Output file to save results (optional)

Now you have inited the experience pool using `local_file` backend (start on `http://localhost:8001`). The `local_file_to_library.py` script or use the following `curl` command:
```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "bfcl_v1",
    "action": "dump",
    "path": "./library"
  }'
```
can convert the local file to the experience library (default in `./library/bfcl_v1.jsonl`).

Next time, you can import this previously exported experience data to populate the new started workspace with existing knowledge:
```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "bfcl_v1",
    "action": "load",
    "path": "./library"
  }'
```


### 4. Run Experiments on Validation Set

Run you can compare agent performance on the validation set with experience (`use_experience=True`) and without experience:

```bash
# remember to change the configuration options, e.g., `data_path=./data/multiturn_data_base_val.jsonl`
python run_bfcl.py
```

After running experiments, analyze the statistical results:

```bash
python run_exp_statistic.py
```

**What this script does:**
- Processes all result files in `./exp_result/`
- Calculates best@k metrics for different k values
- Generates a summary table showing performance comparisons
- Saves results to `experiment_summary.csv`
