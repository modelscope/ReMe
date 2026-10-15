"""JSON contracts for loss-aware, tool-only context compaction."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


class CompactionOptions(BaseModel):
    """Decision model budgets are independent of the host model's context budget."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    keep_threshold: float = Field(default=0.5, ge=0, le=1)
    preserve_recent_messages: int = Field(default=6, ge=0, strict=True)
    max_state_tokens: int = Field(default=25000, gt=0, strict=True)
    max_request_tokens: int = Field(default=30000, gt=0, strict=True)
    truncate_head_chars: int = Field(default=300, ge=0, strict=True)
    max_concurrency: int = Field(default=4, ge=1, le=32, strict=True)
    total_timeout_seconds: float = Field(default=30, gt=0)


class CompactionRequest(BaseModel):
    """AgentScope 2.x message snapshots; no live objects or provider credentials."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    messages: list[dict[str, JsonValue]]
    goal: str = ""
    protected_message_ids: list[str] = Field(default_factory=list)
    protected_call_ids: list[str] = Field(default_factory=list)
    eligible_tool_names: list[str] = Field(default_factory=list)
    options: CompactionOptions = Field(default_factory=CompactionOptions)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, messages):
        """Reject ambiguous envelopes while retaining unknown block fields."""
        for message in messages:
            if message.get("role") not in ("user", "assistant", "system"):
                raise ValueError("Each message needs a user, assistant, or system role.")
            content = message.get("content")
            if not isinstance(content, list) or any(not isinstance(block, dict) for block in content):
                raise ValueError("Each message needs a list of content block objects.")
        return messages


class CallDecision(BaseModel):
    """A decision identifies an unambiguous pair in the original snapshot."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str
    call_id: str
    action: Literal["keep", "drop_result", "drop_call"]
    reason: str
    keep_call: float | None = Field(default=None, ge=0, le=1)
    keep_result: float | None = Field(default=None, ge=0, le=1)


class CompactionResult(BaseModel):
    """A proposed snapshot; the host owns durability, budgets, and commit."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: Literal[1] = 1
    messages: list[dict[str, JsonValue]]
    decisions: list[CallDecision] = Field(default_factory=list)
    changed: bool
    reason: Literal["compacted", "no_candidates", "no_change"]
    stats: dict[str, JsonValue] = Field(default_factory=dict)
