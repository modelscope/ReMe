# ========== Standard and Third-party Imports ==========
import os
import time
import json
import psutil
import statistics
import openai
from loguru import logger
from rich.progress import Progress
from Config.config import TaskConfig
from collections import defaultdict
from llm_client.llm_client import LLMClient
from World_client.env_client import EnvClient
from EM_client.em_client import EMClient
from Summarizer.summarizer import summarize_experience, generate_context
from concurrent.futures import ThreadPoolExecutor, as_completed
from tasks.utils import extract_task, insert_context_before_task, get_task_difficulty

exp_name = "W_0103"
w_id = "w_0102"

llm_client = LLMClient(api_key="sk-wE5x9PGlWJn3lwlllprnobZqsWhsfxuc47dobxXYTb0LZM0D", base_url="http://8.130.177.212:3000/v1")

def run_environment_interaction(client, agent, instance_id, max_interactions) -> int:

    output = None
    for i in range(max_interactions):
        code = agent.next_code_block(output)
        action = {"role": "assistant", "content": code}
        result = client.step(instance_id, action)
        output = result["state"].get('content', '')

        # Terminate early if the environment signals completion
        if result.get('is_terminated', False):
            print(f"Terminated after {i + 1} turns")
            break
    return client.evaluate(instance_id)


class ReactAgent:
    """
    Agent for proposing the next code block, maintaining
    conversation history and interacting with the LLM API.
    """
    def __init__(self, history, llm_client):
        self.history: list[dict] = history  # Initial conversation context
        self.llm_client = llm_client

    def next_code_block(self, last_execution_output: str | None = None) -> str:

        if last_execution_output is not None:
            self.history.append({"role": "user", "content": last_execution_output})
        code = None
        max_tries = 3
        sleep_sec = 3
        for attempt in range(max_tries):
            try:
                time.sleep(sleep_sec)
                code = llm_client.call_llm(self.history)
                break
            except openai.OpenAIError as e:
                logger.error(f"Rate limit error in LLM call on attempt: {attempt + 1}/{max_tries}:{str(e)}")

                #Wait 5 seconds before retrying again
                if attempt < max_tries - 1:
                    logger.info(f"Rate limit exceeded, retrying in {sleep_sec * 2} seconds")
                    time.sleep(sleep_sec * 2)
            except Exception as e:
                logger.exception(f"Unexpected error in LLM call: {str(e)}")

        if code is None:
            logger.error(f"Failed to generate code after all retries.")
        self.history.append({"role": "assistant", "content": code})
        return code

def evaluate_task(task_id: str, count: int, config: TaskConfig) -> dict:
    """
    Executes a single task (multiple runs if best_at > 1), records results, returns highest result.
    """
    em_client = EMClient(base_url="http://0.0.0.0:8003")
    app_client = EnvClient(base_url="http://localhost:9000")
    task_difficulty = get_task_difficulty(task_id)
    runs = []

    try:
        for i in range(config.best_at):
            print("\n\n" + "*" * 20 + f" Task: {count} | {config.sample_size} " + "*" * 20)
            # --- New env & agent every run
            init_response = app_client.create_instance(config.env_type, task_id)
            instance_id = init_response["info"]["instance_id"]
            init_content = init_response["state"]["content"]

            if config.run_with_experience:
                task_instruction = extract_task(init_content)
                enhanced_content = generate_context(em_client, task_instruction, w_id)
                prompt = insert_context_before_task(init_content, enhanced_content)
                history = [{"role": "user", "content": prompt}]
            else:
                history = [{"role": "user", "content": init_content}]

            agent = ReactAgent(history, llm_client)

            # Run or evaluate task as per configuration
            score = run_environment_interaction(app_client, agent, instance_id, config.max_interactions)
            runs.append((score, agent.history.copy(), init_response))
            print(f"Task id: {task_id} | Run #{i + 1} | Score: {score}")

            try:
                success = app_client.release_instance(instance_id)
                print(f"Instance released: {success}")
            except Exception as e:
                logger.exception(f"Failed to release {instance_id}: {str(e)}")

        #Find best run
        max_score, max_score_history, max_score_init_response = max(runs, key=lambda x: x[0])

        # Output task run summary to terminal
        print(f"task_id: {task_id} \n"
              f"difficulty: {task_difficulty} \n"
              f"Score: {max_score} out of {[r[0] for r in runs]} \n")

        result = {
            'task_id': task_id,
            'difficulty': task_difficulty,
            'score': max_score
        }

        history_dir = f"/Users/seanlu/PycharmProjects/Simple_ReAct/experiments/{exp_name}"
        output_filename = os.path.join(history_dir, f"history_{config.experiment_name}_{task_id}.json")


        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, "w") as f:
            json.dump(max_score_history, f, indent=2)

        # Save summarized experience for later training or review
        if config.create_exp:
            experience_dir = f"/Users/seanlu/PycharmProjects/Simple_ReAct/experiments/Experiences/{exp_name}"
            experience_filename = os.path.join(experience_dir, f"{task_id}.json")
            os.makedirs(os.path.dirname(experience_filename), exist_ok=True)
            instruction = extract_task(max_score_init_response["state"]["content"])
            summarize_experience(em_client, instruction, max_score_history , experience_filename, w_id)
        return result

    except Exception as e:
        logger.exception(f"Exception in evaluate_task for task_id: {task_id}: {str(e)}")
        # Return a failure result for error tracking/statistics
        return {
            "task_id": task_id,
            "difficulty": task_difficulty,
            "score": 0,
            "error": str(e)
        }
        # Always attempt to release any used environment instance to prevent resource leaks


# ========== Parallel Experiment Pipeline ==========
def main():
    # ---- Load experiment configuration, tasks, and dataset ----
    main_app_client = EnvClient(base_url="http://localhost:9000")
    env_type = "appworld"
    task_ids = main_app_client.get_task_ids(env_type)
    sample_size = 57
    experiment_name = exp_name
    max_interactions = 35
    all_results = []

    config = TaskConfig(
        experiment_name=experiment_name, max_interactions=max_interactions, sample_size=sample_size,
        env_type=env_type, run_with_experience=False, create_exp=False, best_at = 2
    )

    # ---- Launch N parallel workers for multiprocessing ----
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for idx, task_id in enumerate(task_ids[:sample_size]):
            futures.append(executor.submit(evaluate_task, task_id, idx + 1, config))

        with Progress() as progress:
            task = progress.add_task("[green]Running experiments...", total=sample_size)
            for idx, future in enumerate(as_completed(futures)):
                result = future.result()
                all_results.append(result)
                # Log memory usage in progress bar
                mem_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
                progress.update(
                    task,
                    advance=1,
                    description=f"Mem: {mem_mb:.1f} MB | {len(all_results)}/{sample_size} complete"
                )

    difficulty_scores = defaultdict(list)
    for res in all_results:
        if 'difficulty' in res and 'score' in res:
            difficulty_scores[res['difficulty']].append(res['score'])

    for diff, scores in sorted(difficulty_scores.items()):
        avg = statistics.mean(scores) if scores else 0
        print(f"Difficulty {diff}: {len(scores)} tasks, Average Score: {avg}")

    print(f"Overall Average: {statistics.mean([r['score'] for r in all_results])}")
    print(f"Best of: {config.best_at}")

if __name__ == "__main__":
    main()
