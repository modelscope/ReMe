import datetime
from pathlib import Path

from loguru import logger
from pydantic import Field

from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.module.prompt.prompt_mixin import PromptMixin
from experiencemaker.module.reward_fn.base_reward_fn import BaseRewardFn
from experiencemaker.schema.reward import Reward
from experiencemaker.schema.trajectory import Trajectory, Message
from experiencemaker.utils.util_function import get_html_match_content


class SimpleCompareRewardFn(BaseRewardFn, PromptMixin):
    llm: BaseLLM | None = Field(default=None)
    eval_times: int = Field(default=5)
    prompt_file_path: Path = Path(__file__).parent / "simple_compare_reward_fn_prompt.yaml"

    def execute(self, trajectory: Trajectory = None, comp_traj: Trajectory = None, **kwargs) -> Reward:
        query = trajectory.query
        answer1 = trajectory.answer
        answer2 = comp_traj.answer
        logger.info("=" * 10 + f"answer1\n{answer1}\n" + "=" * 10 + f"answer2\n{answer2}\n")

        valid_cnt = 0
        better_cnt = 0
        for i in range(self.eval_times):
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user_prompt = self.prompt_handler.compare_prompt.format(
                now_time=now_time,
                query=query,
                answer1=answer1,
                answer2=answer2)

            messages = [Message(content=user_prompt)]
            action_msg = self.llm.chat(messages=messages)

            rule: str = get_html_match_content(action_msg.content, "rule")
            rule_based_comparison: str = get_html_match_content(action_msg.content, "rule_based_comparison")
            result: str | None = get_html_match_content(action_msg.content, "result")
            logger.info(f"round.{i} rule={rule} rule_based_comparison={rule_based_comparison} result={result}")
            if result:
                result = result.lower()
                if "plan1" in result and "plan2" in result:
                    logger.warning(f"both plan exists in result={result}")

                elif "plan1" in result:
                    valid_cnt += 1
                    better_cnt += 1

                elif "plan2" in result:
                    valid_cnt += 1

                else:
                    logger.warning(f"no plan exists in result={result}")

        outcome = 0
        if valid_cnt > 0:
            outcome = better_cnt / valid_cnt
        return Reward(outcome=outcome)
