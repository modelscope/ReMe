# Personal Memory Retrieve Ops

## SetQueryOp

### Functionality
`SetQueryOp` prepares the query for memory retrieval by setting the query and its associated timestamp into the context. It's the first operation in the personal memory retrieval flow.

### Parameters
- `op.set_query_op.params.timestamp`: (Optional) Integer timestamp to use instead of the current time. If not provided, the current timestamp will be used.

### Implementation Details
The operation:
1. Takes the query from the context (which is guaranteed to exist as a flow input requirement)
2. Sets a timestamp (either current time or from parameters)
3. Stores the query and timestamp as a tuple in the context for downstream operations

## ExtractTimeOp

### Functionality
`ExtractTimeOp` identifies and extracts time-related information from the query. It uses an LLM to analyze the query text and determine any temporal references or constraints.

### Parameters
- `op.extract_time_op.params.language`: Language for time extraction (defaults to "en")

### Implementation Details
The operation:
1. Checks if the query contains datetime keywords
2. If time-related words are found, it prepares a prompt for the LLM with:
   - System instructions
   - Few-shot examples
   - The user's query and current time
3. Parses the LLM response to extract time information (year, month, day, etc.)
4. Stores the extracted time dictionary in the context for downstream operations

## RetrieveMemoryOp

### Functionality
`RetrieveMemoryOp` retrieves memories from the vector store based on the query. It extends the `RecallVectorStoreOp` class to provide memory retrieval functionality.

### Parameters
- `op.retrieve_memory_op.params.recall_key`: Key in the context to use as the query (default: "query")
- `op.retrieve_memory_op.params.top_k`: Maximum number of memories to retrieve (default: 3)
- `op.retrieve_memory_op.params.threshold_score`: (Optional) Minimum similarity score for memories (filters out memories below this threshold)

### Implementation Details
The operation:
1. Retrieves the query from the context
2. Searches the vector store for relevant memories based on the query
3. Removes duplicate memories
4. Filters memories by threshold score if specified
5. Stores the retrieved memories in the context for downstream operations

## SemanticRankOp

### Functionality
`SemanticRankOp` ranks memories based on their semantic relevance to the query using an LLM. This improves the quality of retrieved memories by considering deeper semantic relationships beyond vector similarity.

### Parameters
- `op.semantic_rank_op.params.enable_ranker`: Whether to enable semantic ranking (default: true)
- `op.semantic_rank_op.params.output_memory_max_count`: Maximum number of memories to output (default: 10)

### Implementation Details
The operation:
1. Retrieves the memory list from the context
2. If ranking is enabled and there are more memories than the output limit:
   - Removes duplicates based on content
   - Formats memories for LLM ranking
   - Asks the LLM to rank memories by relevance on a scale of 0.0 to 1.0
   - Parses the ranking results and applies scores to memories
3. Sorts memories by score
4. Stores the ranked memories in the context for downstream operations

## FuseRerankOp

### Functionality
`FuseRerankOp` performs the final reranking of memories by combining multiple factors: semantic scores, memory types, and temporal relevance. It also formats the final output.

### Parameters
- `op.fuse_rerank_op.params.fuse_score_threshold`: Minimum score threshold for memories (default: 0.1)
- `op.fuse_rerank_op.params.fuse_ratio_dict`: Dictionary of memory type to score multiplier ratios (default: {"conversation": 0.5, "observation": 1, "obs_customized": 1.2, "insight": 2.0})
- `op.fuse_rerank_op.params.fuse_time_ratio`: Score multiplier for time-relevant memories (default: 2.0)
- `op.fuse_rerank_op.params.output_memory_max_count`: Maximum number of memories to output (default: 5)

### Implementation Details
The operation:
1. Retrieves extracted time information and memory list from the context
2. For each memory:
   - Checks if the memory score is above the threshold
   - Applies a type-based adjustment factor based on the memory type
   - Determines time relevance by matching memory time metadata with extracted time
   - Calculates the final score by multiplying the original score by type and time factors
3. Sorts memories by the reranked scores
4. Selects the top-K memories based on the output limit
5. Formats memories for output with timestamps if available
6. Stores both the formatted output and the memory list in the context

## PrintMemoryOp

### Functionality
`PrintMemoryOp` formats the retrieved memories for display to the user. It provides a clean, structured representation of the memory content.

### Parameters
No specific parameters for this operation.

### Implementation Details
The operation:
1. Retrieves the memory list from the context
2. Formats each memory with:
   - Memory index
   - When to use information
   - Content
   - Additional metadata (if available)
3. Joins the formatted memories into a single string
4. Stores the formatted string in the context as the response answer

## ReadMessageOp

### Functionality
`ReadMessageOp` fetches unmemorized chat messages from the context. This is useful for retrieving recent conversations that haven't been processed into memories yet.

### Parameters
- `op.read_message_op.params.contextual_msg_max_count`: Maximum number of contextual messages to retrieve (default: 10)

### Implementation Details
The operation:
1. Retrieves chat messages from the context
2. Filters for messages that:
   - Are not marked as memorized
   - Contain the target name
3. Flattens the messages into a single list
4. Sorts messages by creation time if available
5. Stores the filtered messages back in the context
