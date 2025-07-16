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
        if request.traj_list:
            self.context.set_context("trajectories", request.traj_list)
        elif request.trajectories:
            self.context.set_context("trajectories", request.trajectories)
        else:
            logger.error("No trajectories is recognized. Please send requests containing traj_list.")

        trajectories: List[Trajectory] = self.context.get_context("trajectories", [])
        
        if not trajectories:
            logger.warning("No trajectories found in context")
            return

        # Validate trajectories
        valid_trajectories = self._validate_trajectories(trajectories)
        logger.info(f"Validated {len(valid_trajectories)} out of {len(trajectories)} trajectories")

        # Classify trajectories
        classified = self._classify_trajectories(valid_trajectories)
        logger.info(f"Classified trajectories - Success: {len(classified['success'])}, "
                   f"Failure: {len(classified['failure'])}, All: {len(classified['all'])}")

        # Set context for downstream operators
        self.context.set_context("success_trajectories", classified['success'])
        self.context.set_context("failure_trajectories", classified['failure'])
        self.context.set_context("all_trajectories", classified['all'])

    def _validate_trajectories(self, trajectories: List[Trajectory]) -> List[Trajectory]:
        """Validate trajectory validity"""
        valid_trajectories = []
        
        for traj in trajectories:
            if self._is_valid_trajectory(traj):
                valid_trajectories.append(traj)
            else:
                logger.debug("Invalid trajectory filtered out")
                
        return valid_trajectories

    def _is_valid_trajectory(self, traj: Trajectory) -> bool:
        """Check if trajectory is valid"""
        if traj is None:
            return False
        if not hasattr(traj, 'score') or traj.score is None:
            return False
        if not hasattr(traj, 'messages') or not traj.messages or len(traj.messages) == 0:
            return False
        return True

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