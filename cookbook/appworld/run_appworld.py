import os
import time
import requests

import ray
from ray import logger

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../.env")

import json
from pathlib import Path

from appworld import load_task_ids

from appworld_react_agent import AppworldReactAgent


def handle_api_response(response: requests.Response):
    """Handle API response with proper error checking"""
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

    return response.json()


def delete_workspace(workspace_id: str, api_url: str = "http://0.0.0.0:8002/"):
    """Delete the current workspace from the vector store"""
    response = requests.post(
        url=f"{api_url}vector_store",
        json={
            "workspace_id": workspace_id,
            "action": "delete",
        }
    )

    result = handle_api_response(response)
    if result:
        print(f"Workspace '{workspace_id}' deleted successfully")


def dump_memory(workspace_id: str, path: str = "./", api_url: str = "http://0.0.0.0:8002/"):
    """Dump the vector store memories to disk"""
    response = requests.post(
        url=f"{api_url}vector_store",
        json={
            "workspace_id": workspace_id,
            "action": "dump",
            "path": path,
        }
    )

    result = handle_api_response(response)
    if result:
        print(f"Memory dumped to {path}")


def load_memory(workspace_id: str, path: str = "docs/library", api_url: str = "http://0.0.0.0:8002/"):
    """Load memories from disk into the vector store"""
    response = requests.post(
        url=f"{api_url}vector_store",
        json={
            "workspace_id": workspace_id,
            "action": "load",
            "path": path,
        }
    )

    result = handle_api_response(response)
    if result:
        print(f"Memory loaded from {path}")


def run_agent(dataset_name: str, experiment_suffix: str, max_workers: int, num_runs: int = 1, use_task_memory: bool = False, make_task_memory: bool = False, workspace_id: str="appworld_v1", api_url: str = "http://0.0.0.0:8002/") :
    experiment_name = dataset_name + "_" + experiment_suffix
    path: Path = Path(f"./exp_result")
    path.mkdir(parents=True, exist_ok=True)

    task_ids = load_task_ids(dataset_name)
    result: list = []

    def dump_file():
        with open(path / f"{experiment_name}.jsonl", "a") as f:
            for x in result:
                f.write(json.dumps(x) + "\n")

    if max_workers > 1:
        future_list: list = []
        for i in range(max_workers):
            # Assign tasks to each worker, ensuring each task runs num_runs times
            worker_task_ids = task_ids[i::max_workers]
            actor = AppworldReactAgent.remote(index=i,
                                              task_ids=worker_task_ids,
                                              experiment_name=experiment_name,
                                              num_runs=num_runs,
                                              use_task_memory=use_task_memory,
                                              make_task_memory=make_task_memory,
                                              workspace_id=workspace_id,
                                              api_url=api_url)
            future = actor.execute.remote()
            future_list.append(future)
            time.sleep(1)
        logger.info("submit complete")

        for i, future in enumerate(future_list):
            t_result = ray.get(future)
            if t_result:
                if isinstance(t_result, list):
                    result.extend(t_result)
                else:
                    result.append(t_result)

            logger.info(f"worker {i + 1}/{max_workers} complete")
        dump_file()

    else:
        for index, task_id in enumerate(task_ids):
            agent = AppworldReactAgent(index=index,
                                     task_ids=[task_id],
                                     experiment_name=experiment_name,
                                     num_runs=num_runs,
                                     use_task_memory=use_task_memory,
                                     make_task_memory=make_task_memory,
                                     workspace_id=workspace_id,
                                     api_url=api_url)
            task_results = agent.execute()
            if isinstance(task_results, list):
                result.extend(task_results)
            else:
                result.append(task_results)
        dump_file()


def main():
    max_workers = 8
    num_runs = 1  # Run each task once
    workspace_id = "appworld"
    api_url = "http://0.0.0.0:8002/"
    
    if max_workers > 1:
        ray.init(num_cpus=8)
    
    # Clean up workspace before starting
    logger.info("Deleting workspace...")
    delete_workspace(workspace_id=workspace_id, api_url=api_url)
    
    # First run to build task memories
    logger.info("Start load experiments to build task memories")
    load_memory(workspace_id=workspace_id, api_url=api_url)
    # run_agent(dataset_name="dev", experiment_suffix="build-memory",
    #           max_workers=max_workers, num_runs=1,
    #           use_task_memory=False, make_task_memory=True,
    #           workspace_id=workspace_id, api_url=api_url)

    for i in range(num_runs):

        # Run experiments with task memory
        logger.info("Start running experiments with task memory")
        run_agent(dataset_name="dev", experiment_suffix=f"with-memory", 
                  max_workers=max_workers, num_runs=1, 
                  use_task_memory=True, make_task_memory=False,
                  workspace_id=workspace_id, api_url=api_url)

        # Run experiments without task memory
        logger.info("Start running experiments without task memory")
        run_agent(dataset_name="dev", experiment_suffix=f"no-memory",
                  max_workers=max_workers, num_runs=1,
                  use_task_memory=False, make_task_memory=False,
                  workspace_id=workspace_id, api_url=api_url)



if __name__ == "__main__":
    main()