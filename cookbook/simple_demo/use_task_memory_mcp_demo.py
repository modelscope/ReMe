#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Memory Demo for MemoryScope using MCP Client

This script demonstrates how to use the task memory capabilities of MemoryScope
through the MCP client interface. It shows how to run an agent, summarize conversations,
retrieve memories, and manage the memory workspace.
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional

from fastmcp import Client
from mcp.types import CallToolResult
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
MCP_URL = "http://0.0.0.0:8002/sse/"
WORKSPACE_ID = "test_workspace"


async def delete_workspace(client: Client) -> None:
    """
    Delete the current workspace from the vector store
    
    Args:
        client: MCP client instance
        
    Returns:
        None
    """
    try:
        result = await client.call_tool(
            "vector_store",
            arguments={
                "workspace_id": WORKSPACE_ID,
                "action": "delete",
            }
        )
        print(f"Workspace '{WORKSPACE_ID}' deleted successfully")
    except Exception as e:
        print(f"Error deleting workspace: {e}")


async def run_agent(client: Client, query: str, dump_messages: bool = False) -> List[Dict[str, Any]]:
    """
    Run the agent with a specific query
    
    Args:
        client: MCP client instance
        query: The query to send to the agent
        dump_messages: Whether to save messages to a file
        
    Returns:
        List of message objects from the conversation
    """
    try:
        result = await client.call_tool(
            "react",
            arguments={"query": query}
        )
        
        # Extract and display the answer
        response_data = json.loads(result.content)
        answer = response_data.get("answer", "")
        print(f"Agent response: {answer}")

        # Get the conversation messages
        messages = response_data.get("messages", [])

        # Optionally save messages to file
        if dump_messages and messages:
            with open("messages.jsonl", "w") as f:
                f.write(json.dumps(messages, indent=2, ensure_ascii=False))
            print(f"Messages saved to messages.jsonl")
        
        return messages
    except Exception as e:
        print(f"Error running agent: {e}")
        return []


async def run_summary(client: Client, messages: List[Dict[str, Any]], enable_dump_memory: bool = True) -> None:
    """
    Generate a summary of conversation messages and create task memories
    
    Args:
        client: MCP client instance
        messages: List of message objects from a conversation
        enable_dump_memory: Whether to save memory list to a file
        
    Returns:
        None
    """
    if not messages:
        print("No messages to summarize")
        return

    try:
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
        
        # Extract memory list from response
        memory_list = response_data.get("metadata", {}).get("memory_list", [])
        print(f"Memory list: {memory_list}")

        # Optionally save memory list to file
        if enable_dump_memory and memory_list:
            with open("task_memory.jsonl", "w") as f:
                f.write(json.dumps(memory_list, indent=2, ensure_ascii=False))
            print(f"Memory saved to task_memory.jsonl")
    except Exception as e:
        print(f"Error running summary: {e}")


async def run_retrieve(client: Client, query: str) -> str:
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
                "workspace_id": WORKSPACE_ID,
                "query": query,
            }
        )
        
        response_data = json.loads(result.content)
        
        # Extract and return the answer
        answer = response_data.get("answer", "")
        print(f"Retrieved memory: {answer}")
        return answer
    except Exception as e:
        print(f"Error retrieving memory: {e}")
        return ""


async def run_agent_with_memory(client: Client, query_first: str, query_second: str, enable_dump_memory: bool = True) -> List[Dict[str, Any]]:
    """
    Run the agent with memory augmentation
    
    This function demonstrates how to use task memory to enhance agent responses:
    1. First run the agent with the second query to build memory
    2. Then summarize the conversation to create memories
    3. Retrieve relevant memories for the first query
    4. Run the agent with the first query augmented with retrieved memories
    
    Args:
        client: MCP client instance
        query_first: The query to run with memory augmentation
        query_second: The query to build initial memories
        enable_dump_memory: Whether to save memory list to a file
        
    Returns:
        List of message objects from the final conversation
    """
    # Run agent with second query to build initial memories
    print(f"\n--- Building memories with query: '{query_second}' ---")
    messages = await run_agent(client, query=query_second)

    # Summarize conversation to create memories
    print("\n--- Summarizing conversation to create memories ---")
    await run_summary(client, messages, enable_dump_memory)
    await asyncio.sleep(1)

    # Retrieve relevant memories for the first query
    print(f"\n--- Retrieving memories for query: '{query_first}' ---")
    retrieved_memory = await run_retrieve(client, query_first)

    # Run agent with first query augmented with retrieved memories
    print(f"\n--- Running agent with memory-augmented query ---")
    augmented_query = f"{retrieved_memory}\n\nUser Question:\n{query_first}"
    print(f"Augmented query: {augmented_query}")
    messages = await run_agent(client, query=augmented_query)
    
    return messages


async def dump_memory(client: Client, path: str = "./") -> None:
    """
    Dump the vector store memories to disk
    
    Args:
        client: MCP client instance
        path: Directory path to save the memories
        
    Returns:
        None
    """
    try:
        result = await client.call_tool(
            "vector_store",
            arguments={
                "workspace_id": WORKSPACE_ID,
                "action": "dump",
                "path": path,
            }
        )
        print(f"Memory dumped to {path}")
    except Exception as e:
        print(f"Error dumping memory: {e}")


async def load_memory(client: Client, path: str = "./") -> None:
    """
    Load memories from disk into the vector store
    
    Args:
        client: MCP client instance
        path: Directory path to load the memories from
        
    Returns:
        None
    """
    try:
        result = await client.call_tool(
            "vector_store",
            arguments={
                "workspace_id": WORKSPACE_ID,
                "action": "load",
                "path": path,
            }
        )
        print(f"Memory loaded from {path}")
    except Exception as e:
        print(f"Error loading memory: {e}")


async def main() -> None:
    """
    Main function to demonstrate task memory workflow
    """
    # Define example queries
    query1 = "Analyze Xiaomi Corporation"
    query2 = "Analyze the company Tesla."

    print("=== Task Memory Demo (MCP Client) ===")

    async with Client(MCP_URL) as client:
        # Step 1: Clean up workspace
        print("\n1. Deleting workspace...")
        await delete_workspace(client)

        # Step 2: Run agent with first query and save messages
        print("\n2. Running agent with first query...")
        await run_agent(client, query=query1, dump_messages=True)

        # Step 3: Demonstrate memory-augmented agent
        print("\n3. Running memory-augmented agent workflow...")
        await run_agent_with_memory(client, query_first=query1, query_second=query2)

        # Step 4: Demonstrate memory persistence
        print("\n4. Dumping memory to disk...")
        await dump_memory(client)

        print("\n5. Loading memory from disk...")
        await load_memory(client)

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
