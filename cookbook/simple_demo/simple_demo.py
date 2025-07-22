import json

import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace1"


def run_agent(query: str, dump_messages: bool = False):

    response = requests.post(url=base_url + "agent", json={"query": query})
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


def run_summary(messages: list, dump_experience: bool = True):
    response = requests.post(url=base_url + "summarizer", json={
        "workspace_id": workspace_id,
        "traj_list": [
            {"messages": messages, "score": 1.0}
        ]
    })

    if response.status_code != 200:
        print(response.text)
        return

    response = response.json()
    experience_list = response["experience_list"]
    if dump_experience:
        with open("experience.jsonl", "w") as f:
            f.write(json.dumps(experience_list, indent=2, ensure_ascii=False))


def run_retriever(query: str):
    response = requests.post(url=base_url + "retriever", json={
        "workspace_id": workspace_id,
        "query": query,
    })

    if response.status_code != 200:
        print(response.text)
        return ""

    response = response.json()
    experience_merged: str = response["experience_merged"]
    print(f"experience_merged={experience_merged}")
    return experience_merged


def run_agent_with_experience(query_first: str, query_second: str, dump_experience: bool = True):
    # messages = run_agent(query=query_second)
    # run_summary(messages, dump_experience)
    experience_merged = run_retriever(query_first)
    messages = run_agent(query=f"{experience_merged}\n\nUser Question:\n{query_first}")
    return messages


def dump_experience():
    response = requests.post(url=base_url + "vector_store", json={
        "workspace_id": workspace_id,
        "action": "dump",
        "path": "./",
    })

    if response.status_code != 200:
        print(response.text)
        return

    print(response.json())


def load_experience():
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

    # run_agent(query=query1, dump_messages=True)
    # run_agent_with_experience(query_first=query1, query_second=query2)
    # dump_experience()
    load_experience()
