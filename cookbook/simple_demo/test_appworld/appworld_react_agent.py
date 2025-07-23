import json
import os

os.environ["APPWORLD_ROOT"] = "."
from dotenv import load_dotenv

load_dotenv("../../../.env")

import re
import time

from appworld import AppWorld, load_task_ids
from jinja2 import Template
from loguru import logger
from openai import OpenAI

from prompt import PROMPT_TEMPLATE

@ray.remote
class AppworldReactAgent:
    """A minimal ReAct Agent for AppWorld tasks."""

    def __init__(self,
                 task_id: str,
                 experiment_name: str,
                 model_name: str = "qwen3-8b",
                 temperature: float = 0.9,
                 max_interactions: int = 50,
                 max_response_size: int = 2000):

        self.task_id: str = task_id
        self.experiment_name: str = experiment_name
        self.model_name: str = model_name
        self.temperature: float = temperature
        self.max_interactions: int = max_interactions
        self.max_response_size: int = max_response_size

        self.world: AppWorld = AppWorld(task_id=task_id, experiment_name=experiment_name)
        self.history: list[dict] = self.prompt_messages()

    def call_llm(self, messages: list) -> str:
        for i in range(100):
            try:
                client = OpenAI()
                # Change this function to modify the base llm
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=400,
                    extra_body={"enable_thinking": False},
                    seed=0)

                return response.choices[0].message.content

            except Exception as e:
                logger.exception(f"encounter error with {e.args}")
                time.sleep(1 + i * 10)

        return "call llm error"

    def prompt_messages(self) -> list[dict]:
        dictionary = {"supervisor": self.world.task.supervisor, "instruction": self.world.task.instruction}
        prompt = Template(PROMPT_TEMPLATE.lstrip()).render(dictionary)
        # Extract and return the OpenAI JSON formatted messages from the prompt
        messages: list[dict] = []
        last_start = 0
        for match in re.finditer("(USER|ASSISTANT|SYSTEM):\n", prompt):
            last_end = match.span()[0]
            if len(messages) == 0:
                if last_end != 0:
                    raise ValueError(
                        f"Start of the prompt has no assigned role: {prompt[:last_end]}"
                    )
            else:
                messages[-1]["content"] = prompt[last_start:last_end]
            role_type = match.group(1).lower()
            messages.append({"role": role_type, "content": None})
            last_start = match.span()[1]
        messages[-1]["content"] = prompt[last_start:]
        return messages

    def next_code_block(self) -> str:
        return self.call_llm(self.history)

    def next_step(self, code: str) -> str:
        output = self.world.execute(code)
        if len(output) > self.max_response_size:
            logger.warning(f"output exceed max size={len(output)}")
            output = output[:self.max_response_size]
        return output

    def get_reward(self) -> float:
        tracker = self.world.evaluate()
        num_passes = len(tracker.passes)
        num_failures = len(tracker.failures)
        return num_passes / (num_passes + num_failures)

    def execute(self):
        try:
            with self.world:
                before_score = self.get_reward()
                logger.info(f"instruction={self.world.task.instruction} before_score={before_score:.4f}")

                for i in range(self.max_interactions):
                    code = self.next_code_block()
                    self.history.append({"role": "assistant", "content": code})

                    output = self.next_step(code)
                    self.history.append({"role": "user", "content": output})

                    logger.info(f"task_id={self.task_id} iteration={i} "
                                f"code=\n{code}\n output=\n{output}\n "
                                f"score={self.get_reward():.4f}")

                    if self.world.task_completed():
                        break

                after_score = self.get_reward()
                uplift_score = after_score - before_score
                result = {
                    "task_id": self.task_id,
                    "experiment_name": self.experiment_name,
                    "task_completed": self.world.task_completed(),
                    "before_score": before_score,
                    "after_score": after_score,
                    "uplift_score": uplift_score,
                    "task_history": self.history,
                }

                return result

        except Exception as e:
            logger.exception(f"encounter error with {e.args}")
            return {}


def main():
    dataset_name = "train"
    task_ids = load_task_ids(dataset_name)
    agent = AppworldReactAgent(task_id=task_ids[0], experiment_name=f"jinli_{dataset_name}")
    result = agent.execute()
    logger.info(f"result={json.dumps(result)}")


if __name__ == "__main__":
    main()
