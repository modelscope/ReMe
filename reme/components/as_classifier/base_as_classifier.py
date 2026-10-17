"""Lifecycle-managed wrappers for AgentScope classifier models."""

from abc import abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..base_component import BaseComponent
from ...enumeration import ComponentEnum

if TYPE_CHECKING:
    from agentscope.classifier import ClassifierResponse


class BaseAsClassifier(BaseComponent):
    """Classify shared text or JSON state with named probabilistic questions."""

    component_type = ComponentEnum.AS_CLASSIFIER

    @abstractmethod
    async def __call__(
        self,
        state: str | dict,
        questions: Mapping[str, Any],
    ) -> "ClassifierResponse":
        """Return typed answers; concrete components own provider resources."""
