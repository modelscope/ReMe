# MCP Quick Start Guide

This guide will help you get started with ReMe using the Model Context Protocol (MCP) interface for seamless
integration with MCP-compatible clients.

## 🚀 What You'll Learn

- How to set up and configure ReMe MCP server
- How to connect to the server using Python MCP clients
- How to use task memory operations through MCP
- How to build experience-enhanced agents with MCP integration

## 📋 Prerequisites

- Python 3.12+
- LLM API access (OpenAI or compatible)
- Embedding model API access
- MCP-compatible client (Claude Desktop, or custom MCP client)

## 🛠️ Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install reme-ai
```

### Option 2: Install from Source

```bash
git clone https://github.com/modelscope/ReMe.git
cd ReMe
pip install .
```

## ⚙️ Environment Setup

Create a `.env` file in your project directory:

```bash
FLOW_EMBEDDING_API_KEY=sk-xxxx
FLOW_EMBEDDING_BASE_URL=https://xxxx/v1

FLOW_LLM_API_KEY=sk-xxxx
FLOW_LLM_BASE_URL=https://xxxx/v1
```

## 🚀 Building an MCP Server with ReMe

ReMe provides a flexible framework for building MCP servers that can communicate using either STDIO or SSE (Server-Sent
Events) transport protocols.

### Starting the MCP Server

#### Option 1: STDIO Transport (Recommended for MCP clients)

```bash
reme \
  backend=mcp \
  mcp.transport=stdio \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

#### Option 2: SSE Transport (Server-Sent Events)

```bash
reme \
  backend=mcp \
  mcp.transport=sse \
  http_service.port=8001 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

The SSE server will start on `http://localhost:8002/sse`

### Configuring MCP Server for Claude Desktop

To integrate with Claude Desktop, add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reme": {
      "command": "reme",
      "args": [
        "backend=mcp",
        "mcp.transport=stdio",
        "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
        "embedding_model.default.model_name=text-embedding-v4",
        "vector_store.default.backend=local_file"
      ]
    }
  }
}
```

This configuration:

1. Registers a new MCP server named "reme"
2. Specifies the command to launch the server (`reme`)
3. Configures the server to use STDIO transport
4. Sets the LLM and embedding models to use
5. Configures the vector store backend

### Advanced Server Configuration Options

For more advanced use cases, you can configure the server with additional parameters:

```bash
# Full configuration example
reme \
  backend=mcp \
  mcp.transport=stdio \
  http_service.host=0.0.0.0 \
  http_service.port=8002 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=elasticsearch \
```

## 🔌 Using Python Client to Call MCP Services

The ReMe framework provides a Python client for interacting with MCP services. This section focuses specifically on
using the `summary_task_memory` and `retrieve_task_memory` tools.

### Setting Up the Python MCP Client

First, install the required packages:

```bash
pip install fastmcp dotenv
```

Then, create a basic client connection:

```python
import asyncio
from fastmcp import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL (for SSE transport)
MCP_URL = "http://0.0.0.0:8002/sse/"
WORKSPACE_ID = "my_workspace"


async def main():
    async with Client(MCP_URL) as client:
        # Your MCP operations will go here
        pass


if __name__ == "__main__":
    asyncio.run(main())
```

### Using the Task Memory Summarizer

The `summary_task_memory` tool transforms conversation trajectories into valuable task memories:

```python
async def run_summary(client, messages):
    """
    Generate a summary of conversation messages and create task memories
    
    Args:
        client: MCP client instance
        messages: List of message objects from a conversation
        
    Returns:
        None
    """
    try:
        result = await client.call_tool(
            "summary_task_memory",
            arguments={
                "workspace_id": "my_workspace",
                "trajectories": [
                    {"messages": messages, "score": 1.0}
                ]
            }
        )

        # Parse the response
        import json
        response_data = json.loads(result.content)

        # Extract memory list from response
        memory_list = response_data.get("metadata", {}).get("memory_list", [])
        print(f"Created memories: {memory_list}")

        # Optionally save memories to file
        with open("task_memory.jsonl", "w") as f:
            f.write(json.dumps(memory_list, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error running summary: {e}")
```

### Using the Task Memory Retriever

The `retrieve_task_memory` tool allows you to retrieve relevant memories based on a query:

```python
async def run_retrieve(client, query):
    """
    Retrieve relevant task memories based on a query
    
    Args:
        client: MCP client instance
        query: The query to retrieve relevant memories
        
    Returns:
        String containing the retrieved memory answer
    """
    try:
        result = await client.call_tool(
            "retrieve_task_memory",
            arguments={
                "workspace_id": "my_workspace",
                "query": query,
            }
        )

        # Parse the response
        import json
        response_data = json.loads(result.content)

        # Extract and return the answer
        answer = response_data.get("answer", "")
        print(f"Retrieved memory: {answer}")
        return answer

    except Exception as e:
        print(f"Error retrieving memory: {e}")
        return ""
```

### Complete Memory-Augmented Agent Example

Here's a complete example showing how to build a memory-augmented agent using the MCP client:

```python
import json
import asyncio
from fastmcp import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
MCP_URL = "http://0.0.0.0:8002/sse/"
WORKSPACE_ID = "test_workspace"


async def run_agent(client, query):
    """Run the agent with a specific query"""
    result = await client.call_tool(
        "react",
        arguments={"query": query}
    )

    response_data = json.loads(result.content)
    answer = response_data.get("answer", "")
    messages = response_data.get("messages", [])

    return messages


async def run_summary(client, messages):
    """Generate task memories from conversation"""
    result = await client.call_tool(
        "summary_task_memory",
        arguments={
            "workspace_id": WORKSPACE_ID,
            "trajectories": [
                {"messages": messages, "score": 1.0}
            ]
        }
    )

    response_data = json.loads(result.content)
    memory_list = response_data.get("metadata", {}).get("memory_list", [])

    return memory_list


async def run_retrieve(client, query):
    """Retrieve relevant task memories"""
    result = await client.call_tool(
        "retrieve_task_memory",
        arguments={
            "workspace_id": WORKSPACE_ID,
            "query": query,
        }
    )

    response_data = json.loads(result.content)
    answer = response_data.get("answer", "")

    return answer


async def memory_augmented_workflow():
    """Complete memory-augmented agent workflow"""
    query1 = "Analyze Xiaomi Corporation"
    query2 = "Analyze the company Tesla."

    async with Client(MCP_URL) as client:
        # Step 1: Build initial memories with query2
        print(f"Building memories with: '{query2}'")
        messages = await run_agent(client, query=query2)

        # Step 2: Summarize conversation to create memories
        print("Creating memories from conversation")
        memory_list = await run_summary(client, messages)
        print(f"Created {len(memory_list)} memories")

        # Step 3: Retrieve relevant memories for query1
        print(f"Retrieving memories for: '{query1}'")
        retrieved_memory = await run_retrieve(client, query1)

        # Step 4: Run agent with memory-augmented query
        print("Running memory-augmented agent")
        augmented_query = f"{retrieved_memory}\n\nUser Question:\n{query1}"
        final_messages = await run_agent(client, query=augmented_query)

        # Extract the agent's final answer
        final_answer = ""
        for msg in final_messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                final_answer = msg.get("content")
                break

        print(f"Memory-augmented response: {final_answer}")


# Run the workflow
if __name__ == "__main__":
    asyncio.run(memory_augmented_workflow())
```

### Managing Vector Store with MCP

You can also manage your vector store through MCP:

```python
async def manage_vector_store(client):
    # Delete a workspace
    await client.call_tool(
        "vector_store",
        arguments={
            "workspace_id": WORKSPACE_ID,
            "action": "delete",
        }
    )

    # Dump memories to disk
    await client.call_tool(
        "vector_store",
        arguments={
            "workspace_id": WORKSPACE_ID,
            "action": "dump",
            "path": "./backups/",
        }
    )

    # Load memories from disk
    await client.call_tool(
        "vector_store",
        arguments={
            "workspace_id": WORKSPACE_ID,
            "action": "load",
            "path": "./backups/",
        }
    )
```

## 🐛 Common Issues and Troubleshooting

### MCP Server Won't Start
- Check if the required ports are available (for SSE transport)
- Verify your API keys in `.env` file
- Ensure Python version is 3.12+
- Check MCP transport configuration

### MCP Client Connection Issues
- For STDIO: Ensure the command path is correct in your MCP client config
- For SSE: Verify the server URL and port accessibility
- Check firewall settings for SSE connections

### No Memories Retrieved

- Make sure you've run the summarizer tool first to create memories
- Check if workspace_id matches between operations
- Verify vector store backend is properly configured

### API Connection Errors
- Confirm LLM_BASE_URL and API keys are correct
- Test API access independently
- Check network connectivity
