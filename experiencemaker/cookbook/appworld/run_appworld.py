import os
import time

import ray
from ray import logger

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../.env")

import json
from pathlib import Path

from appworld import load_task_ids

from appworld_react_agent import AppworldReactAgent


def run_agent(model_name: str, dataset_name: str, experiment_suffix: str, max_workers: int, num_runs: int = 1, enable_thinking: bool=False, use_experience: bool = False, workspace_id: str="appworld", exp_url: str = "http://0.0.0.0:8001/") :
    experiment_name = dataset_name + "_" + experiment_suffix
    if enable_thinking:
        path: Path = Path(f"./exp_result/{model_name}/with_think")
    else:
        path: Path = Path(f"./exp_result/{model_name}/no_think")
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
                                              model_name=model_name,
                                              enable_thinking=enable_thinking,
                                              task_ids=worker_task_ids,
                                              experiment_name=experiment_name,
                                              num_runs=num_runs,
                                              use_experience=use_experience,
                                              workspace_id=workspace_id,
                                              exp_url=exp_url)
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
                                       model_name=model_name,
                                       enable_thinking=enable_thinking,
                                       task_ids=[task_id],
                                       experiment_name=experiment_name,
                                       num_runs=num_runs,
                                       use_experience=use_experience)
            task_results = agent.execute()
            if isinstance(task_results, list):
                result.extend(task_results)
            else:
                result.append(task_results)
        dump_file()


def main():
    max_workers = 12
    num_runs = 4  # Run each task 4 times
    if max_workers > 1:
        ray.init(num_cpus=8)

    logger.info("Start running experiments without experience")
    for i in range(num_runs):
        run_agent(
            model_name="qwen3-8b",
            dataset_name="test_normal", 
            experiment_suffix=f"no-exp-1015-new_prompt_nosplit_new", 
            max_workers=max_workers, 
            num_runs=1,
            enable_thinking=True,
            use_experience=False, 
            workspace_id="appworld_v1"
        )

    # logger.info("Start running experiments with experience")
    # for i in range(num_runs):
    #     run_agent(
    #       dataset_name="dev", 
    #       experiment_suffix=f"add-exp", 
    #       max_workers=max_workers, 
    #       num_runs=1, 
    #       use_experience=True,
    #       enable_thinking=False,
    #       workspace_id="appworld_v1"
    #     )



if __name__ == "__main__":
    main()