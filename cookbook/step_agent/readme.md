# Step Summarizer & Context Generator

A step-level experience extraction and context generation system for the ExperienceMaker framework.

## Overview

This system provides advanced step-level experience extraction and context generation capabilities:

- **StepSummarizer**: Extracts reusable experiences from individual steps or step sequences in trajectories
- **StepContextGenerator**: Retrieves and utilizes step-level experiences to provide relevant context for agent execution

## Key Features

### StepSummarizer Features
- **Trajectory segmentation** into meaningful step sequences
- **Step-level experience extraction** from successful and failed trajectories
- **Similarity-based comparison** for finding related experiences and compare between success and failure cases
- **Experience validation** for quality assurance

### StepContextGenerator Features
- **Score-based filtering** for quality control
- **Llm reranking** for reranking after recalling
- **Context rewriting** to make experiences more relevant to current tasks
- **Hybrid retrieval** combining vector search with LLM reranking

## Configuration Options

### StepSummarizer Parameters
- `enable_step_segmentation`: Enable trajectory segmentation (default: False)
- `enable_similarity_search`: Enable similarity search for comparison (default: False)
- `enable_experience_validation`: Enable experience validation (default: True)
- `max_retries`: Maximum retries for LLM calls (default: 3)

### StepContextGenerator Parameters
- `enable_llm_rerank`: Enable LLM-based reranking (default: True)
- `enable_context_rewrite`: Enable context rewriting (default: True)
- `enable_score_filter`: Enable score-based filtering (default: False)
- `vector_retrieve_top_k`: Number of candidates to retrieve (default: 15)
- `final_top_k`: Final number of experiences to return (default: 5)
- `min_score_threshold`: Minimum score threshold for filtering (default: 0.3)

## Quick Start

### 1. Basic Setup
```bash
# Start the service with default configuration
bash run.sh


### 3. Run Examples
```python
# Test the system with example trajectories
python examples.py
```

## Usage Examples

### Extract Step Experiences
```python
# Extract experiences from trajectories
summarizer_request = {
    "trajectories": [successful_trajectory, failed_trajectory],
    "workspace_id": "my_workspace",
    # "metadata": {
    #     "em_config": {
    #         "summarizer": {
    #             "backend": "step",
    #             "enable_step_segmentation": True,
    #             "enable_similarity_search": True,
    #             "enable_experience_validation": True
    #         }
    #     }
    # }
}

response = requests.post(f"{SERVICE_URL}/summarizer", json=summarizer_request)
```

### Generate Context
```python
# Generate context for current task
context_request = {
    "trajectory": current_trajectory,
    "workspace_id": "my_workspace",
    # "metadata": {
    #     "em_config": {
    #         "context_generator": {
    #             "backend": "step",
    #             "enable_llm_rerank": True,
    #             "enable_context_rewrite": True,
    #             "final_top_k": 5
    #         }
    #     }
    # }
}

response = requests.post(f"{SERVICE_URL}/context_generator", json=context_request)
```