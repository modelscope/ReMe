# FrozenLake Experiment Quick Start Guide

This guide helps you quickly set up and run FrozenLake experiments with ExperienceMaker integration.

## Env Setup

### 1. Clone the Repository

```bash
git clone https://github.com/modelscope/ExperienceMaker.git
cd ExperienceMaker/cookbook/frozenlake
```

### 2. FrozenLake Environment Setup

Install Gymnasium for FrozenLake environment:

```bash
pip install gymnasium
```

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

Load default experience library for FrozenLake:
```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "frozenlake_no_slippery",
    "action": "dump",
    "path": "./experience_library"
  }'
```
Now you have loaded the default FrozenLake experience library to enable experience-based agent!

## Run Experiments

### 1. Quick Test: Performance Evaluation Only (Default)

Run the main experiment script to test agent performance using existing experience:

```bash
python run_frozenlake.py
```

**What this does:**
- Tests the agent on randomly generated FrozenLake maps
- Uses the default experience library (`frozenlake_no_slippery`)
- Evaluates performance with multiple runs for statistical significance
- Results are automatically saved to `./exp_result/` directory

### 2. Advanced: Training + Testing (Experience Generation)

To create new experiences through training and then test performance:

```bash
python run_frozenlake.py --enable-training
```

**What this does:**
- **Stage 1 (Training)**: Generates new experiences by solving training maps
- **Stage 2 (Testing)**: Evaluates performance using the generated experiences
- Compares baseline performance vs experience-enhanced performance

### 3. Custom Configuration Examples

**Basic customization:**
```bash
python run_frozenlake.py --experiment-name "my_frozenlake_test" --max-workers 8
```

**Enable slippery mode:**
```bash
python run_frozenlake.py --slippery --experiment-name "frozenlake_slippery"
```

**Full training experiment:**
```bash
python run_frozenlake.py \
    --enable-training \
    --experiment-name "frozenlake_training_experiment" \
    --max-workers 8 \
    --training-runs 4 \
    --num-training-maps 50 \
    --test-runs 5 \
    --num-test-maps 100 \
    --slippery
```

**View all available options:**
```bash
python run_frozenlake.py --help
```

### 4. View Experiment Results

After running experiments, analyze the statistical results:

```bash
python run_exp_statistic.py
```

**What this script does:**
- Processes all result files in `./exp_result/`
- Calculates success rates and performance metrics
- Generates a summary table showing performance comparisons
- Saves results to `experiment_summary.csv`

## Configuration Parameters

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `--experiment-name` | `frozenlake_no_slippery` | Name of the experiment |
| `--max-workers` | `4` | Number of parallel workers |
| `--enable-training` | `False` | Enable training phase (experience generation) |
| `--training-runs` | `4` | Number of runs per training map |
| `--num-training-maps` | `50` | Number of training maps |
| `--test-runs` | `1` | Number of runs per test configuration |
| `--num-test-maps` | `100` | Number of test maps to use |
| `--slippery` | `False` | Enable slippery ice mode |

## Understanding Results

The experiment evaluates agent performance on FrozenLake maps:

- **Success Rate**: Percentage of episodes that reach the goal
- **Default Mode**: Uses existing experience library for quick testing
- **Training Mode**: Generates new experiences then tests performance improvement

**Output Files:**
- `./exp_result/*.jsonl`: Raw experiment results
- `./exp_result/experiment_summary.csv`: Statistical summary
- Console output: Real-time progress and metrics