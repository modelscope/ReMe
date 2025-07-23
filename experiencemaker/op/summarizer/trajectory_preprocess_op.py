from typing import List, Dict

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.message import Trajectory
from experiencemaker.schema.request import SummarizerRequest


@OP_REGISTRY.register()
class TrajectoryPreprocessOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Preprocess trajectories: validate and classify"""
        request: SummarizerRequest = self.context.request

        # Classify trajectories
        classified = self._classify_trajectories(request.traj_list)
        logger.info(f"Classified trajectories - Success: {len(classified['success'])}, "
                   f"Failure: {len(classified['failure'])}, All: {len(classified['all'])}")

        # Set context for downstream operators
        self.context.set_context("success_trajectories", classified['success'])
        self.context.set_context("failure_trajectories", classified['failure'])
        self.context.set_context("all_trajectories", classified['all'])

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