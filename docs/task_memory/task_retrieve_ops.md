# Task Memory Retrieval Operations

## BuildQueryOp

### Purpose

Constructs a query for memory retrieval either from a direct query input or by analyzing conversation messages.

### Functionality

- If a direct `query` is provided in the context, it uses that query directly
- If `messages` are provided in the context, it can:
    - **LLM-based**: Use an LLM to generate a focused query based on the conversation context
    - **Simple**: Create a simple query from the last 3 messages without using an LLM
- Raises an error if neither `query` nor `messages` is provided

### Processing Flow

1. **Check for Direct Query**:
   - If `context.query` exists, use it directly
   - This is the most common case when retrieving for a specific task

2. **Build from Messages** (if no direct query):
   - Extract last 3 messages from `context.messages`
   - If `enable_llm_build=true`:
     - Merge all messages into execution_process text
     - Use LLM to analyze and generate a focused query
   - If `enable_llm_build=false`:
     - Truncate each message content to 200 chars
     - Format as "- role: content" for each message
     - Concatenate into a simple query

3. **Set Context**: Store the built query in `context.query` for downstream ops

### Parameters

- `op.build_query_op.params.enable_llm_build` (boolean, default: `true`):
    - When `true`, uses an LLM to generate a query from conversation messages
    - When `false`, creates a simple query by concatenating recent messages
    - LLM-based queries are more focused but require an extra LLM call
    - Simple queries are faster but may be less targeted

### Usage Example

```python
import requests

# Method 1: Direct query (recommended)
response = requests.post(
    url="http://0.0.0.0:8002/retrieve_task_memory",
    json={
        "workspace_id": "my_workspace",
        "query": "How to handle file upload errors in Python?"
    }
)

# Method 2: From messages (when integrated in conversation)
# This is handled internally by the flow when messages are provided
```

### When to Use Which Mode

- **Direct Query**: Most common, use when you know what to search for
- **LLM-based Build**: When you have a conversation and want the LLM to extract the key question
- **Simple Build**: When you want fast retrieval without extra LLM cost

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
- Extracts current conversation context to inform the rewriting process

### Processing Flow

1. **Get Inputs**:
   - `memory_list`: Retrieved and reranked memories from previous ops
   - `query`: The search query
   - `messages`: Current conversation messages (optional)

2. **Format Memories**:
   - Create numbered memory entries with "When to use" and "Content"
   - Example format:
     ```
     Memory 1:
      When to use: [condition]
      Content: [experience]
     ```

3. **LLM Rewrite** (if `enable_llm_rewrite=true`):
   - Extract current context from last 3 messages
   - Provide original formatted memories and current context to LLM
   - LLM adapts the memories to be more relevant to the current query
   - Extracts `rewritten_context` from LLM response (JSON format)

4. **Return**: Set `context.response.answer` to the final formatted/rewritten memories

### Parameters

- `op.rewrite_memory_op.params.enable_llm_rewrite` (boolean, default: `true`):
    - When `true`, uses an LLM to rewrite the memories to make them more relevant and actionable
    - When `false`, simply formats the memories without LLM-based rewriting
    - LLM rewriting makes memories more contextual but adds latency

### Format Examples

**Without LLM Rewrite** (enable_llm_rewrite=false):
```
Memory 1 :
 When to use: When handling file upload errors in web applications
 Content: Use try-except blocks to catch specific exceptions like PermissionError...

Memory 2 :
 When to use: When validating file types before processing
 Content: Check file extensions and MIME types to ensure security...
```

**With LLM Rewrite** (enable_llm_rewrite=true):
```
Based on your question about file upload errors in Python web applications:

1. Error Handling Strategy:
   - Wrap file operations in try-except blocks
   - Catch specific exceptions: PermissionError, IOError, OSError
   - [Adapted from Memory 1]

2. Input Validation:
   - Always validate file types before processing
   - Check both extension and MIME type
   - [Adapted from Memory 2]
```

### When to Enable LLM Rewrite

- **Enable** when:
  - Memories need to be adapted to specific context
  - User query is complex or nuanced
  - Better integration with conversation flow is needed

- **Disable** when:
  - Fast retrieval is prioritized
  - Memories are already clear and relevant
  - Reducing LLM calls and costs is important

## MergeMemoryOp

### Purpose

An alternative to RewriteMemoryOp that merges multiple memories into a single response without using an LLM.

### Functionality

- Collects the content from all memories in the memory list
- Formats them into a single response with a standard structure
- Adds a prompt to consider the helpful parts when answering the question
