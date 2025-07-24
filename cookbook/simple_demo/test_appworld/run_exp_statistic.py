import json
from pathlib import Path

from loguru import logger


def run_exp_statistic():
    path: Path = Path(f"./exp_result")

    for file in path.glob("*.jsonl"):
        with open(file, "r") as f:
            task_completed_list = []
            before_score_list = []
            after_score_list = []
            task_success_list = []
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                task_completed_list.append(1 if data["task_completed"] is True else 0)
                before_score_list.append(data["before_score"])
                after_score_list.append(data["after_score"])
                task_success_list.append(data["after_score"] > 0.9)

            task_completed_ratio = sum(task_completed_list) / len(task_completed_list)
            before_score_ratio = sum(before_score_list) / len(before_score_list)
            after_score_ratio = sum(after_score_list) / len(after_score_list)
            task_success_ratio = sum(task_success_list) / len(task_success_list)
            logger.info(f"task_completed_ratio={task_completed_ratio:.2f} "
                        f"before_score_ratio={before_score_ratio:.2f} "
                        f"after_score_ratio={after_score_ratio:.2f} "
                        f"task_success_ratio={task_success_ratio:.2f}")


if __name__ == "__main__":
    run_exp_statistic()
