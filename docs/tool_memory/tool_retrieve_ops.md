# Tool Memory Retrieval Ops

## RetrieveToolMemoryOp

### Purpose

Retrieves tool memories from the vector database based on tool names, providing usage patterns, best practices, and historical call data.

### Functionality

- Accepts comma-separated tool names as input
- Searches the vector store for exact tool name matches
- Validates that retrieved memories are of type "tool"
- Returns complete tool memories including usage guidelines and call history

### Parameters

This operation has no configurable parameters. It uses the default vector store configuration.

