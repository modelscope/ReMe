"""
Test script for UseMockSearchOp

This script demonstrates how to use the UseMockSearchOp to intelligently
select and execute search tools based on query complexity.
"""
import asyncio
import json

from flowllm.context import FlowContext
from flowllm.app import FlowLLMApp

from reme_ai.agent.tools.use_mock_search_op import UseMockSearchOp


async def test_single_query(op: UseMockSearchOp, query: str):
    """Test a single query and display results."""
    print(f"\n{'=' * 100}")
    print(f"Testing Query: {query}")
    print(f"{'=' * 100}")
    
    context = FlowContext(query=query)
    await op.async_call(context=context)
    
    result = json.loads(context.use_mock_search_result)
    
    print(f"\n📊 Results:")
    print(f"  Selected Tool:    {result['selected_tool']}")
    print(f"  Reasoning:        {result['reasoning']}")
    print(f"  Query Complexity: {result['complexity']}")
    print(f"  Success:          {result['success']}")
    print(f"\n📝 Content:")
    print(f"  {result['content'][:500]}..." if len(result['content']) > 500 else f"  {result['content']}")
    print(f"\n{'=' * 100}\n")
    
    return result


async def main():
    """Run comprehensive tests of UseMockSearchOp."""
    
    print("\n" + "=" * 100)
    print("UseMockSearchOp Test Suite")
    print("=" * 100)
    print("\nThis test demonstrates the intelligent tool selection capability.")
    print("The LLM analyzes each query and selects the most appropriate search tool:\n")
    print("  • SearchToolA: Fast & shallow (best for simple factual queries)")
    print("  • SearchToolB: Balanced (best for medium complexity queries)")
    print("  • SearchToolC: Comprehensive & slow (best for complex research queries)")
    print("=" * 100)
    
    async with FlowLLMApp(load_default_config=True):
        op = UseMockSearchOp()
        
        # Test cases covering different complexities
        test_queries = [
            # Simple queries (should select SearchToolA)
            {
                "query": "What is the capital of France?",
                "expected_tool": "SearchToolA",
                "description": "Simple factual query"
            },
            {
                "query": "When was Python programming language created?",
                "expected_tool": "SearchToolA",
                "description": "Simple historical fact"
            },
            
            # Medium complexity queries (should select SearchToolB)
            {
                "query": "How does quantum computing work?",
                "expected_tool": "SearchToolB",
                "description": "Medium complexity technical explanation"
            },
            {
                "query": "What are the main causes of climate change?",
                "expected_tool": "SearchToolB",
                "description": "Medium complexity scientific question"
            },
            
            # Complex queries (should select SearchToolC)
            {
                "query": "Analyze the impact of artificial intelligence on global economy, employment, and society",
                "expected_tool": "SearchToolC",
                "description": "Complex multi-dimensional analysis"
            },
            {
                "query": "Compare and contrast different renewable energy solutions including their environmental impact, cost-effectiveness, and scalability",
                "expected_tool": "SearchToolC",
                "description": "Complex comparative analysis"
            }
        ]
        
        results = []
        correct_selections = 0
        
        for test_case in test_queries:
            query = test_case["query"]
            expected = test_case["expected_tool"]
            description = test_case["description"]
            
            print(f"\n🔍 Test Case: {description}")
            print(f"   Expected Tool: {expected}")
            
            result = await test_single_query(op, query)
            results.append({
                "test_case": test_case,
                "result": result
            })
            
            # Check if the selection was correct
            if result["selected_tool"] == expected:
                correct_selections += 1
                print(f"   ✅ Correct tool selected!")
            else:
                print(f"   ⚠️  Different tool selected (this may still be valid)")
        
        # Summary
        print("\n" + "=" * 100)
        print("Test Summary")
        print("=" * 100)
        print(f"Total Tests:      {len(test_queries)}")
        print(f"Expected Matches: {correct_selections}/{len(test_queries)}")
        print(f"Success Rate:     {correct_selections/len(test_queries)*100:.1f}%")
        print("\nNote: Tool selection may vary based on LLM reasoning, and different")
        print("      selections don't necessarily indicate errors.")
        print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())

