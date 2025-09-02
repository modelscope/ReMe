# Personal Memory Summary Ops

## InfoFilterOp

### Purpose
Filters messages based on information content scores, retaining only those that include significant information about the user.

### Parameters
- `op.info_filter_op.params.preserved_scores`: Comma-separated string of scores to preserve (default: "2,3")
- `op.info_filter_op.params.info_filter_msg_max_size`: Maximum size of messages to process (default: 200)

### Description
This operation analyzes messages to determine which ones contain valuable personal information. It uses an LLM to score each message on a scale of 0-3:
- 0: No user information
- 1: Hypothetical or fictional content
- 2: General or time-sensitive information
- 3: Clear, important information or explicitly requested records

Only messages with scores specified in `preserved_scores` are retained. Messages are also filtered to exclude those already memorized and to only include messages from the user.

## GetObservationOp

### Purpose
Extracts general observations about the user from messages that don't contain time-related information.

### Parameters
No specific parameters for this operation.

### Description
This operation processes messages that don't contain time-related keywords. It uses an LLM to extract meaningful observations about the user from these messages. Each observation includes:
- Content: The actual observation text
- Keywords: Tags that indicate when this observation might be relevant
- Source message: The original message that led to this observation

The operation creates `PersonalMemory` objects with observation type "personal_info" for each extracted observation.

## GetObservationWithTimeOp

### Purpose
Extracts observations with time context from messages that contain time-related information.

### Parameters
No specific parameters for this operation.

### Description
This operation is the counterpart to `GetObservationOp` but focuses specifically on messages containing time-related keywords. It extracts observations while preserving the time context, which is important for memories related to schedules, appointments, or time-specific preferences.

The operation creates `PersonalMemory` objects with observation type "personal_info_with_time" for each extracted observation, including the time information in the metadata.

## LoadTodayMemoryOp

### Purpose
Loads memories created today from the vector store to prevent duplication and enable updating of recent memories.

### Parameters
- `op.load_today_memory_op.params.top_k`: Maximum number of memories to retrieve (default: 50)

### Description
This operation retrieves memories created on the current day using vector store search with date filtering. It converts vector nodes to memory objects and makes them available for deduplication in subsequent operations. This helps ensure that new observations don't create redundant memories for information already captured earlier in the day.

## ContraRepeatOp

### Purpose
Identifies and removes contradictory or repetitive information from the collected memories.

### Parameters
- `op.contra_repeat_op.params.contra_repeat_max_count`: Maximum number of memories to process (default: 50)
- `op.contra_repeat_op.params.enable_contra_repeat`: Whether to enable contradiction/repetition checking (default: true)

### Description
This operation analyzes the combined memories from previous operations (observation_memories, observation_memories_with_time, today_memories) to identify contradictions or redundancies. It uses an LLM to evaluate each memory and mark it as:
- "Contradiction": Contradicts other memories
- "Contained": Redundant as the information is already contained in other memories
- "None": Unique and should be kept

Memories marked as contradictory or contained are filtered out, and their IDs are tracked for deletion from the vector store.

## LongContraRepeatOp

### Purpose
Performs more sophisticated contradiction and redundancy analysis for longer-term memory management.

### Parameters
- `op.long_contra_repeat_op.params.long_contra_repeat_max_count`: Maximum number of memories to process (default: 50)
- `op.long_contra_repeat_op.params.enable_long_contra_repeat`: Whether to enable this operation (default: true)

### Description
This operation extends the basic contradiction analysis of `ContraRepeatOp` with the ability to resolve conflicts by modifying contradictory memories rather than simply removing them. It's particularly useful for managing long-term personal memories where information might evolve over time.

For contradictory memories, it can either:
- Modify the content to resolve the contradiction
- Remove the memory if it's completely invalidated
- Keep the most accurate/recent information

## UpdateInsightOp

### Purpose
Updates existing insight values based on new observations.

### Parameters
- `op.update_insight_op.params.update_insight_threshold`: Minimum relevance score threshold (default: 0.3)
- `op.update_insight_op.params.update_insight_max_count`: Maximum number of insights to update (default: 5)

### Description
This operation integrates new observations into existing insights about the user. It:
1. Scores insight memories based on relevance to new observations
2. Selects the top insights that meet the relevance threshold
3. Updates each selected insight using an LLM to incorporate the new information
4. Creates updated insight memories with the original ID but new content

This helps maintain accurate and up-to-date insights as new information about the user becomes available.

## GetReflectionSubjectOp

### Purpose
Generates reflection subjects (topics) from personal memories for insight extraction.

### Parameters
- `op.get_reflection_subject_op.params.reflect_obs_cnt_threshold`: Minimum number of memories required for reflection (default: 10)
- `op.get_reflection_subject_op.params.reflect_num_questions`: Maximum number of new subjects to generate (default: 3)

### Description
This operation analyzes a collection of personal memories to identify potential topics for reflection and insight generation. It:
1. Checks if there are sufficient memories for meaningful reflection
2. Extracts existing insight subjects to avoid duplication
3. Uses an LLM to generate new reflection subjects based on memory content
4. Creates insight memory objects for these new subjects

The generated subjects serve as focal points for organizing and synthesizing personal information about the user.

## UpdateVectorStoreOp

### Purpose
Stores the processed memories in the vector database and removes deleted memories.

### Parameters
No specific parameters for this operation.

### Description
This operation is the final step in the personal memory summarization flow. It:
1. Deletes memories that were marked for removal (contradictory or redundant)
2. Inserts new or updated memories into the vector store
3. Records the number of deleted and inserted memories

This ensures that the vector store remains up-to-date with the latest processed memories.
