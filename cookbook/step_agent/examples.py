"""
Step Experience Service Usage Examples

This file demonstrates how to use the step-level experience extraction and context generation service.
"""

import json
import requests
from typing import List, Dict, Any

from experiencemaker.enumeration.role import Role
from experiencemaker.schema.trajectory import Trajectory, Message, ToolCall

# Service configuration
SERVICE_URL = "http://localhost:8001"
WORKSPACE_ID = "test_workspace"


def create_sample_trajectory(query: str, steps: List[Message], done: bool = True) -> Trajectory:
    """Create a sample trajectory for testing"""
    trajectory = Trajectory(
        query=query,
        steps=steps,
        done=done,
        current_step=len(steps) - 1,
        metadata={
            "domain": "coding",
            "task_type": "problem_solving"
        }
    )
    return trajectory


def example_1_extract_step_experiences():
    """Example 1: Extract step-level experiences from trajectories"""
    print("=== Example 1: Extract Step-Level Experiences ===")

    # Create sample successful trajectory
    successful_trajectory = create_sample_trajectory(
        query="How to implement a binary search algorithm?",
        steps=[
            Message(
                role=Role.USER,
                content="How to implement a binary search algorithm?"
            ),
            Message(
                role=Role.ASSISTANT,
                content="I'll help you implement a binary search algorithm. Let me start by explaining the concept.",
                reasoning_content="Need to first explain the concept before implementation"
            ),
            Message(
                role=Role.ASSISTANT,
                content="Here's the implementation:\n\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
                tool_calls=[
                    ToolCall(
                        index=0,
                        id="call_1",
                        name="code_execution",
                        arguments='{"code": "def binary_search(arr, target): ..."}',
                        result="Code executed successfully"
                    )
                ]
            ),
            Message(
                role=Role.TOOL,
                content="Code executed successfully. Binary search implementation is correct."
            )
        ],
        done=True
    )

    # Create sample failed trajectory
    failed_trajectory = create_sample_trajectory(
        query="How to implement a binary search algorithm?",
        steps=[
            Message(
                role=Role.USER,
                content="How to implement a binary search algorithm?"
            ),
            Message(
                role=Role.ASSISTANT,
                content="Here's a binary search:\n\ndef binary_search(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return i\n    return -1",
                reasoning_content="Implementing binary search as linear search by mistake"
            ),
            Message(
                role=Role.TOOL,
                content="Error: This is actually a linear search, not binary search. Binary search requires sorted array and divide-and-conquer approach."
            )
        ],
        done=False
    )

    # Extract experiences using summarizer
    summarizer_request = {
        "trajectories": [successful_trajectory.model_dump(), failed_trajectory.model_dump()]*5,
        "workspace_id": WORKSPACE_ID
    }

    try:
        response = requests.post(f"{SERVICE_URL}/summarizer", json=summarizer_request)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Extracted {len(result['experiences'])} step-level experiences")

        for i, experience in enumerate(result['experiences']):
            print(f"\nExperience {i + 1}:")
            print(f"  Condition: {experience['experience_desc']}")
            print(f"  Content: {experience['experience_content'][:100]}...")
            print(f"  Role: {experience['experience_role']}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error extracting experiences: {e}")


def example_2_generate_step_context():
    """Example 2: Generate context from step-level experiences"""
    print("\n=== Example 2: Generate Step-Level Context ===")

    # Create a new trajectory that needs context
    current_trajectory = create_sample_trajectory(
        query="How to implement a quick sort algorithm?",
        steps=[
            Message(
                role=Role.USER,
                content="How to implement a quick sort algorithm?"
            ),
            Message(
                role=Role.ASSISTANT,
                content="I need to implement a quick sort algorithm. Let me think about the approach.",
                reasoning_content="Quick sort is a divide-and-conquer algorithm"
            )
        ],
        done=False
    )

    # Generate context using context generator
    context_request = {
        "trajectory": current_trajectory.model_dump(),
        "workspace_id": WORKSPACE_ID
    }

    try:
        response = requests.post(f"{SERVICE_URL}/context_generator", json=context_request)
        response.raise_for_status()

        result = response.json()
        context_message = result['context_msg']

        print("✅ Generated step-level context:")
        print(f"Content: {context_message['content']}")

        if 'metadata' in context_message:
            print(f"Metadata: {context_message['metadata']}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error generating context: {e}")


def example_3_full_agent_execution():
    """Example 3: Full agent execution with step-level experience"""
    print("\n=== Example 3: Full Agent Execution with Step Experience ===")

    # Execute agent with step-level context
    agent_request = {
        "query": "Implement a merge sort algorithm with proper error handling",
        "workspace_id": WORKSPACE_ID
    }

    try:
        response = requests.post(f"{SERVICE_URL}/agent_wrapper", json=agent_request)
        response.raise_for_status()

        result = response.json()
        trajectory = result['trajectory']

        print("✅ Agent execution completed:")
        print(f"Query: {trajectory['query']}")
        print(f"Steps: {len(trajectory['steps'])}")
        print(f"Done: {trajectory['done']}")
        print(f"Answer: {trajectory.get('answer', 'No answer')[:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error in agent execution: {e}")


def example_4_custom_configuration():
    """Example 4: Custom configuration for different use cases"""
    print("\n=== Example 4: Custom Configuration Examples ===")

    # Configuration for research-intensive tasks
    research_config = {
        "context_generator": {
            "backend": "step",
            "enable_llm_rerank": True,
            "enable_context_rewrite": True,
            "enable_score_filter": True,
            "vector_retrieve_top_k": 20,
            "final_top_k": 8,
            "min_score_threshold": 0.2
        },
        "summarizer": {
            "backend": "step",
            "enable_step_segmentation": True,
            "enable_similar_comparison": True,
            "enable_experience_validation": True,
            "max_retries": 5
        }
    }

    # Configuration for quick tasks
    quick_config = {
        "context_generator": {
            "backend": "step",
            "enable_llm_rerank": False,
            "enable_context_rewrite": False,
            "enable_score_filter": False,
            "vector_retrieve_top_k": 5,
            "final_top_k": 2,
            "min_score_threshold": 0.5
        },
        "summarizer": {
            "backend": "step",
            "enable_step_segmentation": False,
            "enable_similar_comparison": False,
            "enable_experience_validation": False,
            "max_retries": 1
        }
    }

    print("📋 Research-intensive configuration:")
    print(json.dumps(research_config, indent=2))

    print("\n📋 Quick task configuration:")
    print(json.dumps(quick_config, indent=2))


def main():
    """Run all examples"""
    print("🚀 Step Experience Service Usage Examples")
    print("=" * 50)

    # Wait for service to be ready
    try:
        response = requests.get(f"{SERVICE_URL}/docs")
        print("✅ Service is running and ready")
    except requests.exceptions.RequestException:
        print("❌ Service is not running. Please start the service first:")
        print("   run.sh")
        return

    # Run examples
    example_1_extract_step_experiences()
    # example_2_generate_step_context()
    # example_3_full_agent_execution()
    # example_4_custom_configuration()

    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    main()