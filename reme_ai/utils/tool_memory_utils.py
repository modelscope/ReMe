import random
from datetime import datetime, timedelta
from typing import List, Dict, Any


def create_mock_tool_call_results(tool_name: str, count: int = 30) -> List[Dict[str, Any]]:
    """
    Create mock tool call results for testing

    Args:
        tool_name: Name of the tool to create results for
        count: Number of mock results to create

    Returns:
        List of tool call result dictionaries
    """
    base_time = datetime.now() - timedelta(days=7)
    tool_call_results = []

    if tool_name == "web_search":
        # Scenario 1: Successful searches (15 calls)
        success_queries = [
            "Python asyncio tutorial", "machine learning basics", "React hooks guide",
            "Docker best practices", "SQL optimization tips", "Git workflow strategies",
            "RESTful API design", "microservices architecture", "Redis caching patterns",
            "Kubernetes deployment", "GraphQL advantages", "MongoDB schema design",
            "JWT authentication", "OAuth2 flow", "WebSocket real-time"
        ]

        for i, query in enumerate(success_queries):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=i * 2)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": query,
                    "max_results": random.randint(5, 20),
                    "language": "en",
                    "filter_type": "technical_docs"
                },
                "output": f"Found {random.randint(8, 20)} relevant results for '{query}'. Top results include official documentation, tutorials, and best practice guides.",
                "token_cost": random.randint(100, 300),
                "success": True,
                "time_cost": round(random.uniform(1.5, 3.5), 2)
            })

        # Scenario 2: Poor parameters (8 calls)
        for i in range(8):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=30 + i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"test query {i}",
                    "max_results": 100,
                    "language": "unknown",
                },
                "output": f"Warning: language 'unknown' not supported, using default. Query too generic, returning limited results. Found {random.randint(2, 5)} results.",
                "token_cost": random.randint(50, 150),
                "success": True,
                "time_cost": round(random.uniform(2.0, 4.0), 2)
            })

        # Scenario 3: Timeouts or failures (5 calls)
        for i in range(5):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=54 + i * 4)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"extremely complex query with many conditions {i}",
                    "max_results": 50,
                    "language": "en",
                    "filter_type": "all"
                },
                "output": "Error: Request timeout after 10 seconds. Try simplifying the query or reducing max_results.",
                "token_cost": 20,
                "success": False,
                "time_cost": 10.0
            })

        # Scenario 4: Empty results (2 calls)
        for i in range(2):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=74 + i * 5)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"xyzabc123nonexistent{i}",
                    "max_results": 10,
                    "language": "en",
                },
                "output": "No results found for the given query. Please try different keywords.",
                "token_cost": 30,
                "success": True,
                "time_cost": 1.2
            })

    elif tool_name == "database_query":
        # Scenario 1: Successful queries (12 calls)
        for i in range(12):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "table": f"users_{i % 3}",
                    "query": f"SELECT * FROM table WHERE id > {i * 10}",
                    "limit": random.randint(10, 100)
                },
                "output": f"Query executed successfully. Returned {random.randint(5, 50)} rows in {round(random.uniform(0.1, 0.5), 3)}s.",
                "token_cost": random.randint(20, 80),
                "success": True,
                "time_cost": round(random.uniform(0.1, 0.5), 3)
            })

        # Scenario 2: Slow queries (6 calls)
        for i in range(6):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=36 + i * 4)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "table": "large_table",
                    "query": f"SELECT * FROM large_table WHERE name LIKE '%pattern%' ORDER BY created_at",
                    "limit": 1000
                },
                "output": f"Query executed but took longer than expected. Returned {random.randint(100, 1000)} rows. Consider adding indexes.",
                "token_cost": random.randint(50, 150),
                "success": True,
                "time_cost": round(random.uniform(5.0, 10.0), 2)
            })

        # Scenario 3: Query errors (4 calls)
        for i in range(4):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=60 + i * 5)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "table": "invalid_table",
                    "query": f"SELECT * FROM invalid_table WHERE bad_column = {i}",
                    "limit": 10
                },
                "output": f"Error: Table 'invalid_table' does not exist or column 'bad_column' not found.",
                "token_cost": 10,
                "success": False,
                "time_cost": 0.05
            })

    elif tool_name == "file_processor":
        # Scenario 1: Successful file processing (10 calls)
        file_types = ["csv", "json", "xml", "txt", "pdf"]
        for i in range(10):
            file_type = file_types[i % len(file_types)]
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=i * 4)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "file_path": f"/data/file_{i}.{file_type}",
                    "operation": "read",
                    "encoding": "utf-8"
                },
                "output": f"Successfully processed {file_type.upper()} file. Size: {random.randint(100, 5000)}KB, Records: {random.randint(100, 10000)}",
                "token_cost": random.randint(50, 200),
                "success": True,
                "time_cost": round(random.uniform(1.0, 3.0), 2)
            })

        # Scenario 2: Large file warnings (5 calls)
        for i in range(5):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=40 + i * 6)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "file_path": f"/data/large_file_{i}.csv",
                    "operation": "read",
                    "encoding": "utf-8"
                },
                "output": f"Warning: Large file detected ({random.randint(50, 200)}MB). Processing may take longer. Consider using streaming mode.",
                "token_cost": random.randint(200, 500),
                "success": True,
                "time_cost": round(random.uniform(10.0, 30.0), 2)
            })

        # Scenario 3: File not found (3 calls)
        for i in range(3):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=70 + i * 8)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "file_path": f"/invalid/path/file_{i}.txt",
                    "operation": "read",
                    "encoding": "utf-8"
                },
                "output": "Error: File not found. Please check the file path and ensure the file exists.",
                "token_cost": 10,
                "success": False,
                "time_cost": 0.01
            })

    return tool_call_results[:count]
