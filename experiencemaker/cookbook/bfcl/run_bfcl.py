import os
import time
import ray
from ray import logger

from dotenv import load_dotenv

load_dotenv("../../.env")

import json
from pathlib import Path


from bfcl_agent import BFCLAgent


def run_agent(dataset_name: str, 
              experiment_suffix: str, 
              max_workers: int, 
              num_runs: int = 4, 
              model_name: str = "qwen3-8b",
              data_path: str = "data/multiturn_data_base_val.jsonl",
              answer_path: Path = Path("data/possible_answer"),
              use_experience: bool = False,         
              use_fixed_experience: bool = True,         
              enable_thinking: bool = False,
              experience_base_url: str = "http://0.0.0.0:8001/",
              experience_workspace_id: str = "bfcl_8b_0725"):
    experiment_name = dataset_name + "_" + experiment_suffix
    path: Path = Path(f"./exp_result/{model_name}")
    path.mkdir(parents=True, exist_ok=True)
    
    with open(data_path, "r", encoding="utf-8") as f:
        task_ids = [json.loads(l)["id"] for l in f]

    result: list = []

    def dump_file():
        with open(path / f"{experiment_name}.jsonl", "a") as f:
            for x in result:
                f.write(json.dumps(x) + "\n")

    if max_workers > 1:
        future_list: list = []
        for i in range(max_workers):
            actor = BFCLAgent.remote(
                index=i, 
                task_ids=task_ids[i::max_workers],
                experiment_name=experiment_name,
                data_path=data_path,
                answer_path=answer_path,
                model_name=model_name,
                num_runs=num_runs,
                use_experience=use_experience,
                use_fixed_experience=use_fixed_experience,
                enable_thinking=enable_thinking,
                experience_base_url=experience_base_url,
                experience_workspace_id=experience_workspace_id
            )
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
            agent = BFCLAgent(index=index, 
                              task_ids=[task_id], 
                              experiment_name=experiment_name,
                              num_runs=num_runs,
                              model_name=model_name,
                              data_path=data_path,
                              answer_path=answer_path,
                              enable_thinking=enable_thinking,
                              use_experience=use_experience,
                              use_fixed_experience=use_fixed_experience,
                              experience_base_url=experience_base_url,
                              experience_workspace_id=experience_workspace_id)
            task_results = agent.execute()
            if isinstance(task_results, list):
                result.extend(task_results)
            else:
                result.append(task_results)
        dump_file()

def main():
    max_workers = 4
    num_runs = 4  # Run each task 4 times
    use_experience = True
    use_fixed_experience = True
    experience_base_url = "http://0.0.0.0:8001/"
    experience_workspace_id = "bfcl_v1"
    if max_workers > 1:
        ray.init(num_cpus=4)
    for run_id in range(num_runs):
        run_agent(
            dataset_name="bfcl-multi-turn-base-val", 
            experiment_suffix=f"0813-w-exp-w-think-update-test",
            model_name="qwen3-8b",
            max_workers=max_workers, 
            num_runs=1, 
            data_path="data/multiturn_data_base_val.jsonl",
            answer_path=Path("data/possible_answer"),
            enable_thinking=True,
            use_experience=use_experience,
            use_fixed_experience=use_fixed_experience,
            experience_base_url=experience_base_url,
            experience_workspace_id=experience_workspace_id,
        )


if __name__ == "__main__":
    main()
