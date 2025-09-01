# Task Memory

Task Memory in ReMe.ai is designed to enhance task-solving capabilities by leveraging historical experiences. It provides two core operations: retrieval and summarization of task-related memories.

## Task Memory Retrieval Pipeline

The task memory retrieval pipeline is designed to fetch the most relevant historical experiences based on the current query:

```
build_query_op >> recall_vector_store_op >> rerank_memory_op >> rewrite_memory_op
```

### Pipeline Components

1. **build_query_op**: Processes and optimizes the user query for memory retrieval
2. **recall_vector_store_op**: Retrieves relevant memory experiences from the vector database
3. **rerank_memory_op**: Reranks the retrieved memories based on relevance scores
4. **rewrite_memory_op**: Reformats the memory content for better presentation

### Input Schema
- `query` (str, required): The user query for which relevant task memories are needed

### Description
Retrieves the most relevant top-k memory experiences from historical data based on the current query to enhance task-solving capabilities.

## Task Memory Summary Pipeline

The task memory summary pipeline processes conversation trajectories into structured memory representations:

```
trajectory_preprocess_op >> (success_extraction_op|failure_extraction_op|comparative_extraction_op) >> memory_validation_op >> update_vector_store_op
```

### Pipeline Components

1. **trajectory_preprocess_op**: Preprocesses conversation trajectories for memory extraction
2. **success_extraction_op**: Extracts successful task-solving experiences
3. **failure_extraction_op**: Extracts failed task attempts and lessons learned
4. **comparative_extraction_op**: Extracts comparative experiences and insights
5. **memory_validation_op**: Validates the extracted memory content for accuracy
6. **update_vector_store_op**: Stores the validated memories in the vector database

### Input Schema
- `trajectories` (list, optional): A list of conversation trajectory information, including message content and score. This field is automatically completed by the system.

### Description
Summarizes conversation trajectories or messages into structured memory representations for long-term storage.

## Usage

These pipelines work together to create a continuous learning system where past task experiences inform current task-solving capabilities, improving the overall performance and effectiveness of the AI assistant.