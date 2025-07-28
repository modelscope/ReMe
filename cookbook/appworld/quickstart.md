# AppWorld Experiment Quick Start Guide

This guide helps you quickly set up and run AppWorld experiments with ExperienceMaker integration.

## Env Setup

### 1. Clone the Repository

```bash
git clone https://github.com/modelscope/ExperienceMaker.git
cd ExperienceMaker/cookbook/appworld
```

### 2. Appworld Environment Setup

Create a new conda environment with Python 3.12:

```bash
conda create -p ./appworld-env python==3.12
conda activate ./appworld-env
```

Install required Python packages:

```bash
pip install -r requirements.txt
```

Install AppWorld and download the dataset:

```bash
pip install appworld
appworld install
appworld download data
```

**Note**: The AppWorld data will be saved in the current directory.

### 3. Start ExperienceMaker Service

Install ExperienceMaker (if not already installed)
If you haven't installed the ExperienceMaker environment yet, follow these steps:
```bash
# Go back to the project root
cd ../..

# Create ExperienceMaker environment
conda create -p ./em-env python==3.12
conda activate ./em-env

# Install ExperienceMaker
pip install .
```

Launch the ExperienceMaker service to enable experience library functionality:

```bash
experiencemaker \
  http_service.port=8001 \
  llm.default.model_name=qwen-max-latest \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

add experiences for appworld:
```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "appworld",
    "action": "dump",
    "path": "./experience_library"
  }'
```
Now you have loaded the ExperienceMaker experience library to enable experience-based agent!

### 4. Common Issues

**AppWorld data not found**: Ensure `appworld download data` completed successfully

**pydantic version issue**:  AppWorld depends on an older version of pydantic, which is why a separate environment is needed. If you encounter issues running the experiments, try `pip install appworld` to override the dependencies.



## Run Experiments

### 1. Test: With Experience vs Without Experience

Run the main experiment script to compare performance with and without experience:

```bash
python run_appworld.py
```

**What this does:**
- Runs AppWorld tasks on the development dataset
- Compares agent performance with experience (`use_experience=True`) vs without experience
- Uses multiple workers for parallel processing
- Runs each task multiple times for statistical significance
- Results are automatically saved to `./exp_result/` directory

**Configuration options in `run_appworld.py`:**
- `max_workers`: Number of parallel workers (default: 6)
- `num_runs`: Number of times each task is repeated (default: 4)
- `use_experience`: Whether to use ExperienceMaker experience library

### 2. View Experiment Results

After running experiments, analyze the statistical results:

```bash
python run_exp_statistic.py
```

**What this script does:**
- Processes all result files in `./exp_result/`
- Calculates best@k metrics for different k values
- Generates a summary table showing performance comparisons
- Saves results to `experiment_summary.csv`

**Metrics explained:**
- `best@k`: Takes groups of k runs per task, finds the maximum score in each group, then averages these maximums
- Higher k values show potential performance, lower k values show consistency

**Output Files**

- `./exp_result/*.jsonl`: Raw experiment results for each configuration
- `./exp_result/experiment_summary.csv`: Statistical summary table
- Console output: Real-time progress and summary statistics

## Understanding Results

The experiment compares:
1. **Baseline**: Agent without experience library
2. **With Experience**: Agent enhanced with ExperienceMaker experience library

Key metrics to look for:
- **best@1**: Average performance across all single runs
- **best@k**: Performance when taking the best of k attempts
- Improvement percentage when using experience vs baseline