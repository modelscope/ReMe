import asyncio

from reme_ai import ReMeApp


# ============================================
# Task Memory Management Examples
# ============================================

async def summary_task_memory():
    """
    Experience Summarizer: Learn from execution trajectories
    
    curl -X POST http://localhost:8002/summary_task_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "task_workspace",
        "trajectories": [
          {"messages": [{"role": "user", "content": "Help me create a project plan"}], "score": 1.0}
        ]
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="summary_task_memory",
            workspace_id="task_workspace",
            trajectories=[
                {
                    "messages": [
                        {"role": "user", "content": "Help me create a project plan"}
                    ],
                    "score": 1.0
                }
            ]
        )
        print("Summary Task Memory Result:")
        print(result)


async def retrieve_task_memory():
    """
    Retriever: Get relevant memories
    
    curl -X POST http://localhost:8002/retrieve_task_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "task_workspace",
        "query": "How to efficiently manage project progress?",
        "top_k": 1
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="retrieve_task_memory",
            workspace_id="task_workspace",
            query="How to efficiently manage project progress?",
            top_k=1
        )
        print("Retrieve Task Memory Result:")
        print(result)


# ============================================
# Personal Memory Management Examples
# ============================================

async def summary_personal_memory():
    """
    Memory Integration: Learn from user interactions
    
    curl -X POST http://localhost:8002/summary_personal_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "task_workspace",
        "trajectories": [
          {"messages": [
            {"role": "user", "content": "I like to drink coffee while working in the morning"},
            {"role": "assistant", "content": "I understand, you prefer to start your workday with coffee to stay energized"}
          ]}
        ]
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="summary_personal_memory",
            workspace_id="task_workspace",
            trajectories=[
                {
                    "messages": [
                        {"role": "user", "content": "I like to drink coffee while working in the morning"},
                        {"role": "assistant",
                         "content": "I understand, you prefer to start your workday with coffee to stay energized"}
                    ]
                }
            ]
        )
        print("Summary Personal Memory Result:")
        print(result)


async def retrieve_personal_memory():
    """
    Memory Retrieval: Get personal memory fragments
    
    curl -X POST http://localhost:8002/retrieve_personal_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "task_workspace",
        "query": "What are the users work habits?",
        "top_k": 5
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="retrieve_personal_memory",
            workspace_id="task_workspace",
            query="What are the user's work habits?",
            top_k=5
        )
        print("Retrieve Personal Memory Result:")
        print(result)


# ============================================
# Tool Memory Management Examples
# ============================================

async def add_tool_call_result():
    """
    Record tool execution results
    
    curl -X POST http://localhost:8002/add_tool_call_result \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "tool_workspace",
        "tool_call_results": [
          {
            "create_time": "2025-10-21 10:30:00",
            "tool_name": "web_search",
            "input": {"query": "Python asyncio tutorial", "max_results": 10},
            "output": "Found 10 relevant results...",
            "token_cost": 150,
            "success": true,
            "time_cost": 2.3
          }
        ]
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="add_tool_call_result",
            workspace_id="tool_workspace",
            tool_call_results=[
                {
                    "create_time": "2025-10-21 10:30:00",
                    "tool_name": "web_search",
                    "input": {"query": "Python asyncio tutorial", "max_results": 10},
                    "output": "Found 10 relevant results...",
                    "token_cost": 150,
                    "success": True,
                    "time_cost": 2.3
                }
            ]
        )
        print("Add Tool Call Result:")
        print(result)


async def summary_tool_memory():
    """
    Generate usage guidelines from history
    
    curl -X POST http://localhost:8002/summary_tool_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "tool_workspace",
        "tool_names": "web_search"
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="summary_tool_memory",
            workspace_id="tool_workspace",
            tool_names="web_search"
        )
        print("Summary Tool Memory Result:")
        print(result)


async def retrieve_tool_memory():
    """
    Retrieve tool guidelines before use
    
    curl -X POST http://localhost:8002/retrieve_tool_memory \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "tool_workspace",
        "tool_names": "web_search"
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="retrieve_tool_memory",
            workspace_id="tool_workspace",
            tool_names="web_search"
        )
        print("Retrieve Tool Memory Result:")
        print(result)


# ============================================
# Vector Store Management Example
# ============================================

async def load_vector_store():
    """
    Load pre-built memories
    
    curl -X POST http://localhost:8002/vector_store \
      -H "Content-Type: application/json" \
      -d '{
        "workspace_id": "appworld",
        "action": "load",
        "path": "./docs/library/"
      }'
    """
    async with ReMeApp() as app:
        result = await app.async_execute(
            name="vector_store",
            workspace_id="appworld",
            action="load",
            path="./docs/library/"
        )
        print("Load Vector Store Result:")
        print(result)


# ============================================
# Main Execution
# ============================================

async def main():
    """Run all examples"""
    print("=" * 60)
    print("Task Memory Examples")
    print("=" * 60)
    await summary_task_memory()
    print("\n")
    await retrieve_task_memory()
    
    print("\n" + "=" * 60)
    print("Personal Memory Examples")
    print("=" * 60)
    await summary_personal_memory()
    print("\n")
    await retrieve_personal_memory()
    
    print("\n" + "=" * 60)
    print("Tool Memory Examples")
    print("=" * 60)
    await add_tool_call_result()
    print("\n")
    await summary_tool_memory()
    print("\n")
    await retrieve_tool_memory()
    
    print("\n" + "=" * 60)
    print("Vector Store Examples")
    print("=" * 60)
    await load_vector_store()


if __name__ == "__main__":
    asyncio.run(main())
