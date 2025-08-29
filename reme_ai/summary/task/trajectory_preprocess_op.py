import json
from typing import List, Dict

from flowllm import C, BaseOp
from loguru import logger

from reme_ai.schema import Trajectory


@C.register_op()
class TrajectoryPreprocessOp(BaseOp):
    file_path: str = __file__

    def execute(self):
        """Preprocess trajectories: validate and classify"""
        trajectories: list = self.context.get("trajectories", [])
        # trajectories: List[Trajectory] = [Trajectory(**x) if isinstance(x, dict) else x for x in trajectories]
        new_trajectories: List[Trajectory] = []
        for x in trajectories:
            if isinstance(x, dict):
                x["messages"] = self._modify_tool_calls(x["messages"])
                new_trajectories.append(Trajectory(**x))
            else:
                new_trajectories.append(x)
        trajectories = new_trajectories

        # Classify trajectories
        classified = self._classify_trajectories(trajectories)
        logger.info(f"Classified trajectories - Success: {len(classified['success'])}, "
                   f"Failure: {len(classified['failure'])}, All: {len(classified['all'])}")

        # Set context for downstream operators
        self.context.success_trajectories = classified['success']
        self.context.failure_trajectories = classified['failure']
        self.context.all_trajectories = classified['all']

    def _classify_trajectories(self, trajectories: List[Trajectory]) -> Dict[str, List[Trajectory]]:
        """Classify trajectories based on score threshold"""
        success_trajectories = []
        failure_trajectories = []
        
        success_threshold = self.op_params.get("success_threshold", 1.0)
        
        for traj in trajectories:
            is_success = traj.score >= success_threshold
            
            if is_success:
                success_trajectories.append(traj)
            else:
                failure_trajectories.append(traj)

        return {
            'success': success_trajectories,
            'failure': failure_trajectories,
            'all': trajectories
        }

    def _modify_tool_calls(self, messages: List[Dict]) -> List[Dict]:
        new_messages = []
        
        for msg in messages:
            if 'tool_calls' in msg:
                processed_tool_calls = []
                for tool_call in msg['tool_calls']:
                    tool_type = tool_call.get("type", "function")
                    nested_data = tool_call.get(tool_type, {})
                    tool_call.update({
                        "arguments": json.loads(nested_data.get("arguments", "")),
                        "name": nested_data.get("name", "")
                    })
                    tool_call.pop(tool_type)
                    processed_tool_calls.append(tool_call)
                msg['tool_calls'] = processed_tool_calls
            new_messages.append(msg)
        
        return new_messages