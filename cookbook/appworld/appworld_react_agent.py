import os
from typing import List

from oauthlib.uri_validate import query
from tqdm import tqdm

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../../.env")

import re
import time
import json
import ray
import requests

from appworld import AppWorld, load_task_ids
from jinja2 import Template
from loguru import logger
from openai import OpenAI

from prompt import PROMPT_TEMPLATE, PROMPT_TEMPLATE_WITH_EXPERIENCE


@ray.remote
class AppworldReactAgent:
    """A minimal ReAct Agent for AppWorld tasks."""

    def __init__(self,
                 index: int,
                 task_ids: List[str],
                 experiment_name: str,
                 model_name: str = "qwen3-8b",
                 temperature: float = 0.9,
                 max_interactions: int = 30,
                 max_response_size: int = 4096,
                 num_runs: int = 1,
                 use_experience: bool = False,
                 make_experience: bool = False,
                 base_url: str = "http://0.0.0.0:8001/",
                 workspace_id: str="appworld_8b_0725"):

        self.index: int = index
        self.task_ids: List[str] = task_ids
        self.experiment_name: str = experiment_name
        self.model_name: str = model_name
        self.temperature: float = temperature
        self.max_interactions: int = max_interactions
        self.max_response_size: int = max_response_size
        self.num_runs: int = num_runs
        self.use_experience: bool = use_experience
        self.make_experience: bool = make_experience
        self.base_url = base_url
        self.workspace_id = workspace_id

        self.llm_client = OpenAI()

    def call_llm(self, messages: list) -> str:
        for i in range(100):
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    extra_body={"enable_thinking": False},
                    seed=0)

                return response.choices[0].message.content

            except Exception as e:
                logger.exception(f"encounter error with {e.args}")
                time.sleep(1 + i * 10)

        return "call llm error"

    def prompt_messages(self,world: AppWorld) -> list[dict]:
        if self.use_experience:
            experience = self.get_experience(world.task.instruction)
            logger.info(f"loaded experience: {experience}")
            dictionary = {"supervisor": world.task.supervisor, "instruction": world.task.instruction, "experience": experience}
        else:
            dictionary = {"supervisor": world.task.supervisor, "instruction": world.task.instruction ,"experience": ""}
        print(dictionary)
        prompt = Template(PROMPT_TEMPLATE_WITH_EXPERIENCE.lstrip()).render(dictionary)
        messages: list[dict] = []
        last_start = 0
        # for match in re.finditer("(USER|ASSISTANT|SYSTEM):\n", prompt):
        #     last_end = match.span()[0]
        #     if len(messages) == 0:
        #         if last_end != 0:
        #             raise ValueError(
        #                 f"Start of the prompt has no assigned role: {prompt[:last_end]}"
        #             )
        #     else:
        #         messages[-1]["content"] = prompt[last_start:last_end]
        #     role_type = match.group(1).lower()
        #     messages.append({"role": role_type, "content": None})
        #     last_start = match.span()[1]
        # messages[-1]["content"] = prompt[last_start:]
        messages.append({"role":"user", "content":prompt})
        return messages

    @staticmethod
    def get_reward(world) -> float:
        tracker = world.evaluate()
        num_passes = len(tracker.passes)
        num_failures = len(tracker.failures)
        return num_passes / (num_passes + num_failures)

    def execute(self):
        result = []
        for task_index, task_id in enumerate(tqdm(self.task_ids, desc=f"ray_index={self.index}")):
            # Run each task num_runs times
            for run_id in range(self.num_runs):
                with AppWorld(task_id=task_id, experiment_name=f"{self.experiment_name}_run_{run_id}") as world:
                    history = self.prompt_messages(world=world)
                    before_score = self.get_reward(world)

                    for i in range(self.max_interactions):
                        code = self.call_llm(history)
                        history.append({"role": "assistant", "content": code})

                        output = world.execute(code)
                        if len(output) > self.max_response_size:
                            # logger.warning(f"output exceed max size={len(output)}")
                            output = output[:self.max_response_size]
                        history.append({"role": "user", "content": output})

                        if world.task_completed():
                            break

                    after_score = self.get_reward(world)
                    uplift_score = after_score - before_score
                    t_result = {
                        "task_id": world.task_id,
                        "run_id": run_id,  # Add run_id field
                        "experiment_name": self.experiment_name,
                        "task_completed": world.task_completed(),
                        "before_score": before_score,
                        "after_score": after_score,
                        "uplift_score": uplift_score,
                        "task_history": history,
                    }
                    result.append(t_result)

        if self.make_experience:
            self.make_experience(result)

        return result

    def get_experience(self, query: str):
        response = requests.post(url=self.base_url + "retriever", json={
            "workspace_id": self.workspace_id,
            "query": query,
            "top_k": 5
        })

        if response.status_code != 200:
            print(response.text)
            return ""

        response = response.json()
        print(response)
        experience_merged: str = response["experience_merged"]
        print(f"experience_merged={experience_merged}")
        return experience_merged

    def make_experience(self, result):
        pass


def main():
    dataset_name = "train"
    task_ids = load_task_ids(dataset_name)
    agent = AppworldReactAgent(index=0, task_ids=task_ids[0:1], experiment_name=dataset_name, num_runs=4)
    result = agent.execute()
    logger.info(f"result={json.dumps(result)}")


if __name__ == "__main__":
    main()