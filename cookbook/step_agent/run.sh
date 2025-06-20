#!/bin/bash

# Step Experience Service Startup Script
# This script launches the experiencemaker service with step-level experience extraction and context generation

# StepSummarizer Parameters
# enable_step_segmentation: Segment trajectories into meaningful step sequences
# enable_similar_comparison: Compare similar sequences between success/failure
# enable_experience_validation: Validate experience quality before storage

# StepContextGenerator Parameters
# enable_llm_rerank: Rerank retrieved experiences by relevance using LLM
# enable_context_rewrite: Rewrite context to be more task-specific
# enable_score_filter: Filter experiences by quality scores

echo "Starting Step Experience Service..."

python -m experiencemaker.em_service \
    --port=8001 \
    --llm='{"backend": "openai_compatible", "model_name": "qwen-max-2025-01-25", "temperature": 0.6}' \
    --embedding_model='{"backend": "openai_compatible", "model_name": "text-embedding-v4", "dimensions": 1024}' \
    --vector_store='{"backend": "local_file", "store_dir": "./step_experiences/"}' \
    --context_generator='{"backend": "step", "enable_llm_rerank": true, "enable_context_rewrite": true, "enable_score_filter": false, "vector_retrieve_top_k": 15, "final_top_k": 5, "min_score_threshold": 0.3}' \
    --summarizer='{"backend": "step", "enable_step_segmentation": false, "enable_similar_comparison": false, "enable_experience_validation": true, "max_retries": 3, "max_workers": 16}'

echo "Step Experience Service started on port 8001"