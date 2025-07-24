import os
import time

import ray
from ray import logger

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../../.env")

import json
from pathlib import Path

from appworld import load_task_ids

from appworld_react_agent import AppworldReactAgent


def run_agent(dataset_name: str, experiment_suffix: str, max_workers: int):
    experiment_name = dataset_name + "_" + experiment_suffix
    path: Path = Path(f"./exp_result")
    path.mkdir(parents=True, exist_ok=True)

    task_ids = load_task_ids(dataset_name)
    result: list = []

    def dump_file():
        with open(path / f"{experiment_name}.jsonl", "w") as f:
            for x in result:
                f.write(json.dumps(x) + "\n")

    if max_workers > 1:
        future_list: list = []
        for i in range(max_workers):
            actor = AppworldReactAgent.remote(index=i,
                                              task_ids=task_ids[i::max_workers],
                                              experiment_name=experiment_name)
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

            logger.info(f"{i + 1}/{len(task_ids)} complete")
            dump_file()

    else:
        for index, task_id in enumerate(task_ids):
            agent = AppworldReactAgent(index=index, task_ids=[task_id], experiment_name=experiment_name)
            result.append(agent.execute())
            dump_file()


def main():
    max_workers = 8
    if max_workers > 1:
        ray.init(num_cpus=8)
    run_agent(dataset_name="train", experiment_suffix="v2", max_workers=max_workers)
    run_agent(dataset_name="dev", experiment_suffix="v2", max_workers=max_workers)


if __name__ == "__main__":
    main()
