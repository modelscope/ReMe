# FrozenLake Experiment Quick Start Guide

This guide helps you quickly set up and run FrozenLake experiments with ReMe integration. The FrozenLake experiment demonstrates how task memory can improve an agent's performance in a navigation task.

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/modelscope/ReMe.git
cd ReMe/cookbook/frozenlake
```

### 2. FrozenLake Environment Setup

Install Gymnasium for FrozenLake environment:

```bash
pip install gymnasium
```

This will install:
- gymnasium - for the FrozenLake environment
- ray - for parallel execution
- openai - for LLM API access
- other dependencies

### 3. Start ReMe Service

If you haven't installed ReMe yet, follow these steps:
```bash
# Go back to the project root
cd ../..

# Create a virtual environment (optional)
conda create -p ./reme-env python==3.10
conda activate ./reme-env

# Install ReMe
pip install .
```

Launch the ReMe service to enable memory library functionality:

```bash
reme \
  backend=http \
  http.port=8002 \
  llm.default.model_name=qwen-max-2025-01-25 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

Add your api key for agent:
```bash
export OPENAI_API_KEY="xxx"
export OPENAI_BASE_URL="xxx"
```


## Run Experiments

### 1. Quick Test: Performance Evaluation Only (Default)

Run the main experiment script to test agent performance using existing memory:

```bash
cd cookbook/frozenlake
python run_frozenlake.py
```

**What this does:**
- Tests the agent on randomly generated FrozenLake maps
- Uses the default memory library (`frozenlake_no_slippery`)
- Evaluates performance with multiple runs for statistical significance
- Results are automatically saved to `./exp_result/` directory

### 2. Advanced: Training + Testing (Memory Generation)

To create new memories through training and then test performance:

You can modify the experiment parameters directly in the `run_frozenlake.py` file. The main parameters are in the `main()` function:

```python
def main():
    experiment_name = "frozenlake_no_slippery"  # Name of the experiment
    max_workers = 4                           # Number of parallel workers
    training_runs = 4                         # Runs per training map
    num_training_maps = 50                    # Number of maps for training
    test_runs = 1                             # Runs per test configuration
    num_test_maps = 100                       # Number of test maps
    is_slippery = False                       # Enable slippery mode
```

Key parameters to consider:
- `experiment_name`: Used as the workspace ID for task memory
- `is_slippery`: When True, agent movement becomes stochastic (harder)
- `max_workers`: Increase for faster execution on multi-core systems

### 3. View Experiment Results

After running experiments, analyze the statistical results:

```bash
python run_exp_statistic.py
```

**What this script does:**
- Processes all result files in `./exp_result/`
- Calculates success rates and performance metrics
- Generates a summary table showing performance comparisons
- Analyzes the effect of task memory on performance
- Saves results to `frozenlake_summary.csv`

## Understanding the Implementation

### Key Components

1. **FrozenLakeReactAgent** (`frozenlake_react_agent.py`)
   - Implements a ReAct agent that interacts with the FrozenLake environment
   - Handles task memory retrieval and storage
   - Uses LLM (via OpenAI API) for decision making

2. **Experiment Runner** (`run_frozenlake.py`)
   - Manages the overall experiment flow
   - Handles training and testing phases
   - Uses Ray for parallel execution

3. **Map Manager** (`map_manager.py`)
   - Generates and manages test maps
   - Ensures consistent evaluation across experiments

4. **Statistics Analyzer** (`run_exp_statistic.py`)
   - Processes experiment results
   - Calculates performance metrics
   - Generates comparative analysis

### Output Files

- `./exp_result/*_training.jsonl`: Results from training phase
- `./exp_result/*_test_no_memory.jsonl`: Test results without task memory
- `./exp_result/*_test_with_memory.jsonl`: Test results with task memory
- `./exp_result/frozenlake_summary.csv`: Statistical summary

### Task Memory Mechanism

The task memory system works as follows:

1. **Memory Creation**: During training, successful trajectories are sent to the ReMe service
2. **Memory Retrieval**: During testing, the agent queries relevant memories based on the current map
3. **Memory Application**: The agent uses retrieved memories to guide its decision-making

The experiment demonstrates how task memory can significantly improve performance, especially in challenging environments like the slippery FrozenLake.