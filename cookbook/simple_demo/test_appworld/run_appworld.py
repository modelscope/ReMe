import os

import ray
from ray import logger
from tqdm import tqdm

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../../.env")

import json
from pathlib import Path

from appworld import load_task_ids

from appworld_react_agent import AppworldReactAgent


def run_agent(dataset_name: str, experiment_suffix: str, multi_thread: bool = False):
    experiment_name = dataset_name + "_" + experiment_suffix
    path: Path = Path(f"./exp_result")
    path.mkdir(parents=True, exist_ok=True)

    task_ids = load_task_ids(dataset_name)
    result: list = []

    def dump_file():
        with open(path / f"{experiment_name}.jsonl", "w") as f:
            for x in result:
                f.write(json.dumps(x) + "\n")

    if multi_thread:
        future_list: list = []
        for index, task_id in enumerate(task_ids):
            actor = AppworldReactAgent.remote(index=index, task_id=task_id, experiment_name=experiment_name)
            future = actor.execute.remote()
            future_list.append(future)
        logger.info("submit complete")

        for future in future_list:
            result.append(ray.get(future))
            dump_file()

    else:
        for index, task_id in enumerate(task_ids):
            agent = AppworldReactAgent(index=index, task_id=task_id, experiment_name=experiment_name)
            result.append(agent.execute())
            dump_file()



if __name__ == "__main__":
    # ray.init(num_cpus=8)
    run_agent(dataset_name="train", experiment_suffix="v2")
    # run_agent(dataset_name="dev", experiment_suffix="v2")
