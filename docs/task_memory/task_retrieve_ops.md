# Task Memory Retrieval Ops

## BuildQueryOp

### Purpose

Constructs a query for memory retrieval either from a direct query input or by analyzing conversation messages.

### Functionality

- If a direct `query` is provided in the context, it uses that query
- If `messages` are provided in the context, it can:
    - Use an LLM to generate a query based on the conversation context
    - Or create a simple query from recent messages without using an LLM

### Parameters

- `op.build_query_op.params.enable_llm_build` (boolean, default: `true`):
    - When `true`, uses an LLM to generate a query from conversation messages
    - When `false`, creates a simple query by concatenating recent messages

## RerankMemoryOp

### Purpose

Reranks and filters recalled memories to ensure the most relevant memories are prioritized.

### Functionality

- Reranks memories using LLM-based analysis (optional)
- Filters memories based on quality scores (optional)
- Returns the top-k most relevant memories

### Parameters

- `op.rerank_memory_op.params.enable_llm_rerank` (boolean, default: `true`):
    - When `true`, uses an LLM to rerank memories based on their relevance to the query
- `op.rerank_memory_op.params.enable_score_filter` (boolean, default: `false`):
    - When `true`, filters memories based on their quality scores
- `op.rerank_memory_op.params.min_score_threshold` (float, default: `0.3`):
    - Minimum score threshold for filtering memories when `enable_score_filter` is `true`
- `op.rerank_memory_op.params.top_k` (integer, default: `5`):
    - Number of top memories to retain after reranking

## RewriteMemoryOp

### Purpose

Rewrites and formats the retrieved memories to make them more relevant and actionable for the current context.

### Functionality

- Formats retrieved memories into a structured format
- Can use an LLM to rewrite memories to better fit the current context (optional)
- Generates a cohesive context message from multiple memories

### Parameters

- `op.rewrite_memory_op.params.enable_llm_rewrite` (boolean, default: `true`):
    - When `true`, uses an LLM to rewrite the memories to make them more relevant and actionable
    - When `false`, simply formats the memories without LLM-based rewriting

## MergeMemoryOp

### Purpose

An alternative to RewriteMemoryOp that merges multiple memories into a single response without using an LLM.

### Functionality

- Collects the content from all memories in the memory list
- Formats them into a single response with a standard structure
- Adds a prompt to consider the helpful parts when answering the question