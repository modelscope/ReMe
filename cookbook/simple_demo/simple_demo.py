import json

import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8002/"
workspace_id = "test_workspace4"


def run_agent(query: str, dump_messages: bool = False):
    response = requests.post(url=base_url + "react", json={"query": query})
    if response.status_code != 200:
        print(response.text)
        return []

    response = response.json()

    answer = response["answer"]
    print(answer)

    messages = response["messages"]
    if dump_messages:
        with open("messages.jsonl", "w") as f:
            f.write(json.dumps(messages, indent=2, ensure_ascii=False))

    return messages


def run_summary(messages: list, enable_dump_memory: bool = True):
    response = requests.post(url=base_url + "summary_task_memory_simple", json={
        "workspace_id": workspace_id,
        "trajectories": [
            {"messages": messages, "score": 1.0}
        ]
    })

    if response.status_code != 200:
        print(response.text)
        return

    response = response.json()
    memory_list = response["metadata"]["memory_list"]
    if enable_dump_memory:
        with open("memory.jsonl", "w") as f:
            f.write(json.dumps(memory_list, indent=2, ensure_ascii=False))


def run_retrieve(query: str):
    response = requests.post(url=base_url + "retrieve_task_memory_simple", json={
        "workspace_id": workspace_id,
        "query": query,
    })

    if response.status_code != 200:
        print(response.text)
        return ""

    response = response.json()
    answer: str = response["answer"]
    print(f"answer={answer}")
    return answer


def run_agent_with_memory(query_first: str, query_second: str, enable_dump_memory: bool = True):
    messages = run_agent(query=query_second)
    run_summary(messages, enable_dump_memory)
    retrieved_memory = run_retrieve(query_first)
    messages = run_agent(query=f"{retrieved_memory}\n\nUser Question:\n{query_first}")
    return messages


def dump_memory():
    response = requests.post(url=base_url + "vector_store", json={
        "workspace_id": workspace_id,
        "action": "dump",
        "path": "./",
    })

    if response.status_code != 200:
        print(response.text)
        return

    print(response.json())


def load_memory():
    response = requests.post(url=base_url + "vector_store", json={
        "workspace_id": "test_workspace2",
        "action": "load",
        "path": "./",
    })

    if response.status_code != 200:
        print(response.text)
        return

    print(response.json())


if __name__ == "__main__":
    query1 = "Analyze Xiaomi Corporation"
    query2 = "Analyze the company Tesla."

    run_agent(query=query1, dump_messages=True)
    run_agent_with_memory(query_first=query1, query_second=query2)
    dump_memory()
    load_memory()
