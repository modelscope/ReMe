# Task Memory Summary Ops

## TrajectoryPreprocessOp

### Purpose

Preprocesses trajectories by validating and classifying them based on their score.

### Functionality

- Validates and classifies trajectories as success or failure based on a threshold
- Modifies tool calls in messages to ensure consistent format
- Sets context for downstream operators with classified trajectories

### Parameters

- `op.trajectory_preprocess_op.params.success_threshold` (float, default: `1.0`):
  - The threshold score that determines if a trajectory is considered successful
  - Trajectories with scores greater than or equal to this value are classified as successful

## TrajectorySegmentationOp

### Purpose

Segments trajectories into meaningful step sequences to enable more granular memory extraction.

### Functionality

- Uses LLM to identify logical break points in trajectories
- Adds segmentation information to trajectory metadata
- Enables more focused memory extraction from specific parts of conversations

### Parameters

- `op.trajectory_segmentation_op.params.segment_target` (string, default: `"all"`):
  - Determines which trajectories to segment
  - Options: `"all"`, `"success"`, `"failure"`

## SuccessExtractionOp

### Purpose

Extracts task memories from successful trajectories.

### Functionality

- Processes successful trajectories to identify valuable memories
- Can work with both entire trajectories and segmented step sequences
- Uses LLM to extract structured task memories with when-to-use conditions

### Parameters

No specific parameters beyond the LLM configuration.

## FailureExtractionOp

### Purpose

Extracts task memories from failed trajectories to capture lessons learned from unsuccessful attempts.

### Functionality

- Processes failed trajectories to identify pitfalls and mistakes
- Can work with both entire trajectories and segmented step sequences
- Uses LLM to extract structured task memories with when-to-use conditions

### Parameters

No specific parameters beyond the LLM configuration.

## ComparativeExtractionOp

### Purpose

Extracts comparative task memories by comparing different scoring trajectories.

### Functionality

- Performs "soft comparison" between highest and lowest scoring trajectories
- Can perform "hard comparison" between success and failure trajectories using similarity search
- Identifies key differences that contributed to success or failure

### Parameters

- `op.comparative_extraction_op.params.enable_soft_comparison` (boolean, default: `true`):
  - When `true`, enables comparison between highest and lowest scoring trajectories
- `op.comparative_extraction_op.params.enable_similarity_comparison` (boolean, default: `false`):
  - When `true`, enables similarity-based comparison between success and failure trajectories
- `op.comparative_extraction_op.params.similarity_threshold` (float, default: `0.3`):
  - The threshold for considering two trajectories similar
- `op.comparative_extraction_op.params.max_similarity_sequences` (integer, default: `5`):
  - Maximum number of sequences to compare to avoid computational overload
- `op.comparative_extraction_op.params.max_similarity_pairs` (integer, default: `3`):
  - Maximum number of similar pairs to process

## MemoryValidationOp

### Purpose

Validates the quality of extracted task memories to ensure they are useful and relevant.

### Functionality

- Uses LLM to validate each extracted memory
- Scores memories based on quality and relevance
- Filters out low-quality memories based on validation threshold

### Parameters

- `op.memory_validation_op.params.validation_threshold` (float, default: `0.5`):
  - The minimum score for a memory to be considered valid

## MemoryDeduplicationOp

### Purpose

Removes duplicate task memories to avoid redundancy in the vector store.

### Functionality

- Compares new memories with existing memories in the vector store
- Uses embedding similarity to identify duplicates
- Ensures only unique memories are stored

### Parameters

- `op.memory_deduplication_op.params.similarity_threshold` (float, default: `0.5`):
  - The threshold for considering two memories similar
- `op.memory_deduplication_op.params.max_existing_task_memories` (integer, default: `1000`):
  - Maximum number of existing memories to check against

## SimpleSummaryOp

### Purpose

A simplified version of memory extraction that processes entire trajectories in one step.

### Functionality

- Classifies trajectories as success or failure based on score threshold
- Extracts memories directly from complete trajectories
- Useful for simpler use cases where detailed segmentation is not required

### Parameters

- `op.simple_summary_op.params.success_score_threshold` (float, default: `0.9`):
  - The threshold score that determines if a trajectory is considered successful

## SimpleComparativeSummaryOp

### Purpose

A simplified version of comparative memory extraction.

### Functionality

- Groups trajectories by task ID
- Compares the highest and lowest scoring trajectories for each task
- Extracts comparative insights without complex segmentation

### Parameters

No specific parameters beyond the LLM configuration.