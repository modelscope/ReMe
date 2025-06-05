from typing import List


from beyondagent.core.schema.trajectory import Message, StateMessage, ActionMessage

def format_trajectory_steps(steps: List[Message]) -> str:
    format_steps = []
    step_idx = 0
    single_step = []
    for idx, step in enumerate(steps):
        if isinstance(step, ActionMessage):
            step_idx += 1
            single_step.append(f"** STEP {step_idx} **\n{step.content}")
        elif isinstance(step, StateMessage):
            single_step.append(f"{step.content}")
            format_steps.append("\n".join(single_step))
            single_step = []
    return "\n\n".join(format_steps)