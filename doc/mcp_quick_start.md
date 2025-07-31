# ExperienceMaker MCP Quick Start Guide

This guide will help you get started with ExperienceMaker using the Model Context Protocol (MCP) interface for seamless
integration with MCP-compatible clients.

## 🚀 What You'll Learn

- How to set up ExperienceMaker MCP server
- Connect to the server using MCP clients
- Run an agent and generate experiences via MCP
- Retrieve and apply experiences through MCP tools
- Build experience-enhanced agents with MCP integration

## 📋 Prerequisites

- Python 3.12+
- LLM API access (OpenAI or compatible)
- Embedding model API access
- MCP-compatible client (Claude Desktop, or custom MCP client)

## 🛠️ Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install experiencemaker
```

### Option 2: Install from Source

```bash
git clone https://github.com/modelscope/ExperienceMaker.git
cd ExperienceMaker
pip install .
```

## ⚙️ Environment Setup

Create a `.env` file in your project directory:

```bash
# Required: LLM API configuration
LLM_API_KEY="sk-xxx"
LLM_BASE_URL="https://xxx.com/v1"

# Required: Embedding model configuration  
EMBEDDING_MODEL_API_KEY="sk-xxx"
EMBEDDING_MODEL_BASE_URL="https://xxx.com/v1"

# Optional: Elasticsearch configuration (if using Elasticsearch backend)
ES_HOSTS="http://localhost:9200"
```

## 🚀 Start the MCP Server

### Option 1: STDIO Transport (Recommended for MCP clients)

```bash
experiencemaker_mcp \
  mcp_transport=stdio \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

### Option 2: SSE Transport (Server-Sent Events)

```bash
experiencemaker_mcp \
  mcp_transport=sse \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

The SSE server will start on `http://localhost:8001/sse`

### Elasticsearch Backend

```bash
experiencemaker_mcp \
  mcp_transport=stdio \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=elasticsearch
```

**Setup Elasticsearch:**

```bash
export ES_HOSTS="http://localhost:9200"
# Quick setup using Elastic's official script
curl -fsSL https://elastic.co/start-local | sh
```

📖 **Need Help?** Refer to [Vector Store Setup](vector_store_setup.md) for comprehensive deployment guidance.

## 🔧 Configure MCP Client

### Claude Desktop Configuration

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "experiencemaker": {
      "command": "experiencemaker_mcp",
      "args": [
        "mcp_transport=stdio",
        "llm.default.model_name=qwen3-32b",
        "embedding_model.default.model_name=text-embedding-v4",
        "vector_store.default.backend=local_file"
      ]
    }
  }
}
```

### Custom MCP Client Configuration

If using a custom MCP client, connect to:

- **STDIO**: Use subprocess to communicate with the server
- **SSE**: Connect to `http://localhost:8001/sse`

## 📝 Using ExperienceMaker MCP Tools

The MCP server exposes three main tools:

- `retriever`: Retrieve experiences from workspace
- `summarizer`: Transform trajectories into experiences
- `vector_store`: Manage vector store operations

Note: The `workspace_id` serves as your experience storage namespace. Experiences in different workspaces remain
completely isolated.

### 📊 Using the Summarizer Tool

Transform conversation trajectories into valuable experiences using batch summarization.

**Tool Parameters:**

- `traj_list`: List of trajectories (each containing messages and score)
- `workspace_id`: Workspace identifier (default: "default")
- `config`: Additional configuration parameters (optional)

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio

from experiencemaker.schema.message import Message, Trajectory, Role
from experiencemaker.schema.request import SummarizerRequest
from experiencemaker.service.mcp_client import MCPClient


async def example_summarizer():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        # Create trajectory with conversation
        trajectory = Trajectory(
            messages=[
                Message(role=Role.USER, content="Hello, how can I solve a math problem?"),
                Message(role=Role.ASSISTANT, content="I'd be happy to help! What math problem are you working on?"),
                Message(role=Role.USER, content="What is 2+2?"),
                Message(role=Role.ASSISTANT, content="2+2 equals 4.")
            ],
            score=1.0  # Success score
        )

        request = SummarizerRequest(
            workspace_id="math_workspace",
            traj_list=[trajectory]
        )

        response = await client.call_summarizer(request)
        print("Generated experiences:")
        for experience in response.experience_list:
            print(f"- {experience.content}")


# Run the example
asyncio.run(example_summarizer())
```

</details>

<details>
<summary><b>MCP Tool Call (JSON)</b></summary>

```json
{
  "method": "tools/call",
  "params": {
    "name": "summarizer",
    "arguments": {
      "traj_list": [
        {
          "messages": [
            {
              "role": "user",
              "content": "Hello, how can I solve a math problem?"
            },
            {
              "role": "assistant",
              "content": "I'd be happy to help! What math problem are you working on?"
            },
            {
              "role": "user",
              "content": "What is 2+2?"
            },
            {
              "role": "assistant",
              "content": "2+2 equals 4."
            }
          ],
          "score": 1.0
        }
      ],
      "workspace_id": "math_workspace"
    }
  }
}
```

</details>

### 🔍 Using the Retriever Tool

Intelligently search and retrieve the most relevant experiences from your workspace.

**Tool Parameters:**

- `query`: Search query string
- `messages`: List of conversation messages (optional)
- `top_k`: Number of top experiences to retrieve (default: 1)
- `workspace_id`: Workspace identifier (default: "default")
- `config`: Additional configuration parameters (optional)

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import RetrieverRequest


async def example_retriever():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        request = RetrieverRequest(
            workspace_id="math_workspace",
            query="How to solve basic arithmetic problems?",
            top_k=3
        )

        response = await client.call_retriever(request)
        print(f"Retrieved experiences: {response.experience_merged}")
        print(f"Experience list:")
        for exp in response.experience_list:
            print(f"- {exp.content}")


# Run the example
asyncio.run(example_retriever())
```

</details>

<details>
<summary><b>MCP Tool Call (JSON)</b></summary>

```json
{
  "method": "tools/call",
  "params": {
    "name": "retriever",
    "arguments": {
      "query": "How to solve basic arithmetic problems?",
      "top_k": 3,
      "workspace_id": "math_workspace"
    }
  }
}
```

</details>

### 💾 Using the Vector Store Tool

Manage vector store operations for workspace data.

**Tool Parameters:**

- `action`: Action to perform ("dump", "load", "delete", "copy")
- `workspace_id`: Target workspace identifier
- `src_workspace_id`: Source workspace (for copy operation)
- `path`: File system path (for dump/load operations, default: "./")
- `config`: Additional configuration parameters (optional)

#### Dump Experiences From Vector Store

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import VectorStoreRequest


async def example_dump():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        request = VectorStoreRequest(
            workspace_id="math_workspace",
            action="dump",
            path="./backups/"
        )

        response = await client.call_vector_store(request)
        print(f"Dump result: {response}")


# Run the example
asyncio.run(example_dump())
```

</details>

<details>
<summary><b>MCP Tool Call (JSON)</b></summary>

```json
{
  "method": "tools/call",
  "params": {
    "name": "vector_store",
    "arguments": {
      "action": "dump",
      "workspace_id": "math_workspace",
      "path": "./backups/"
    }
  }
}
```

</details>

#### Load Experiences To Vector Store

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import VectorStoreRequest


async def example_load():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        request = VectorStoreRequest(
            workspace_id="math_workspace",
            action="load",
            path="./backups/"
        )

        response = await client.call_vector_store(request)
        print(f"Load result: {response}")


# Run the example
asyncio.run(example_load())
```

</details>

#### Delete Workspace

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import VectorStoreRequest


async def example_delete():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        request = VectorStoreRequest(
            workspace_id="math_workspace",
            action="delete"
        )

        response = await client.call_vector_store(request)
        print(f"Delete result: {response}")


# Run the example
asyncio.run(example_delete())
```

</details>

#### Copy Workspace

<details open>
<summary><b>Python MCP Client Example</b></summary>

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import VectorStoreRequest


async def example_copy():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        request = VectorStoreRequest(
            workspace_id="math_workspace_copy",
            action="copy",
            src_workspace_id="math_workspace"
        )

        response = await client.call_vector_store(request)
        print(f"Copy result: {response}")


# Run the example
asyncio.run(example_copy())
```

</details>

## 🔄 Complete MCP Workflow Example

Here's a complete example showing the full workflow:

```python
import asyncio
from experiencemaker.service.mcp_client import MCPClient
from experiencemaker.schema.request import SummarizerRequest, RetrieverRequest
from experiencemaker.schema.message import Message, Trajectory, Role

async def complete_workflow():
    async with MCPClient(base_url="http://0.0.0.0:8001/sse") as client:
        print("Available tools:", await client.list_tools())

        # Step 1: Create experiences from trajectories
        trajectory = Trajectory(
            messages=[
                Message(role=Role.USER, content="How do I calculate compound interest?"),
                Message(role=Role.ASSISTANT,
                        content="Compound interest is calculated using the formula A = P(1 + r/n)^(nt), where A is the final amount, P is the principal, r is the annual interest rate, n is the number of times interest is compounded per year, and t is the time in years."),
                Message(role=Role.USER, content="Can you give me an example?"),
                Message(role=Role.ASSISTANT,
                        content="Sure! If you invest $1000 at 5% annual interest compounded monthly for 2 years: A = 1000(1 + 0.05/12)^(12*2) = $1104.94")
            ],
            score=1.0
        )

        summarizer_request = SummarizerRequest(
            workspace_id="finance_workspace",
            traj_list=[trajectory]
        )

        summarizer_response = await client.call_summarizer(summarizer_request)
        print(f"Created {len(summarizer_response.experience_list)} experiences")

        # Step 2: Retrieve relevant experiences
        retriever_request = RetrieverRequest(
            workspace_id="finance_workspace",
            query="How to calculate interest on investments?",
            top_k=2
        )

        retriever_response = await client.call_retriever(retriever_request)
        print(f"Retrieved experiences: {retriever_response.experience_merged}")


# Run the complete workflow
asyncio.run(complete_workflow())
```

## 🎭 Claude Desktop Integration

Once configured with Claude Desktop, you can directly ask Claude to use ExperienceMaker tools:

```
Claude, please use the summarizer tool to create experiences from this conversation about solving math problems, then retrieve similar experiences when I ask about arithmetic.
```

Claude will automatically call the appropriate MCP tools and provide contextually relevant responses based on your
stored experiences.

## 🐛 Common Issues

### MCP Server Won't Start

- Check if the required ports are available (for SSE transport)
- Verify your API keys in `.env` file
- Ensure Python version is 3.12+
- Check MCP transport configuration

### MCP Client Connection Issues

- For STDIO: Ensure the command path is correct in your MCP client config
- For SSE: Verify the server URL and port accessibility
- Check firewall settings for SSE connections

### No Experiences Retrieved

- Make sure you've run the summarizer tool first to create experiences
- Check if workspace_id matches between operations
- Verify vector store backend is properly configured

### API Connection Errors

- Confirm LLM_BASE_URL and API keys are correct
- Test API access independently
- Check network connectivity

## 🔧 Advanced Configuration

### Custom MCP Client Setup

```python
# For STDIO transport
async with MCPClient(enable_sse=False) as client:
    # Your MCP operations here
    pass

# For SSE transport with custom URL
async with MCPClient(base_url="http://custom-host:8001/sse") as client:
    # Your MCP operations here
    pass
```

### Server Configuration Options

```bash
# Full configuration example
experiencemaker_mcp \
  mcp_transport=stdio \
  http_service.host=0.0.0.0 \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  llm.default.api_key=${LLM_API_KEY} \
  llm.default.base_url=${LLM_BASE_URL} \
  embedding_model.default.model_name=text-embedding-v4 \
  embedding_model.default.api_key=${EMBEDDING_MODEL_API_KEY} \
  embedding_model.default.base_url=${EMBEDDING_MODEL_BASE_URL} \
  vector_store.default.backend=elasticsearch \
  vector_store.default.host=localhost \
  vector_store.default.port=9200
```

---

🎯 **You're all set!** You now have a working ExperienceMaker MCP setup that can seamlessly integrate with MCP-compatible
clients and learn from interactions to improve over time through the standardized MCP protocol.

## 📚 Next Steps

- Explore the [Configuration Guide](configuration_guide.md) for advanced customization
- Check out [cookbook examples](../cookbook/) for practical implementations
- Learn about [Vector Store Setup](vector_store_setup.md) for production deployments
- Review the [Operations Documentation](operations_documentation.md) for maintenance procedures