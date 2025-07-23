import os

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../../.env")

import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from appworld import load_task_ids

from appworld_react_agent import AppworldReactAgent


def run_agent(dataset_name: str, max_workers: int, experiment_suffix: str):
    experiment_name = dataset_name + "_" + experiment_suffix
    path: Path = Path(f"./exp_result")
    path.mkdir(parents=True, exist_ok=True)

    task_ids = load_task_ids(dataset_name)
    result: list = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        task_list: list = []
        for index, task_id in enumerate(task_ids):
            agent = AppworldReactAgent(task_id, experiment_name)
            task = executor.submit(agent.execute)
            task_list.append(task)
            time.sleep(1)

        for task in task_list:
            result.append(task.result(timeout=600))

    with open(path / f"{experiment_name}.jsonl", "w") as f:
        for result_item in result:
            f.write(json.dumps(result_item) + "\n")


if __name__ == "__main__":
    run_agent(dataset_name="train", experiment_suffix="v1", max_workers=1)
    # run_agent(dataset_name="dev", experiment_suffix="v1", max_workers=1)
