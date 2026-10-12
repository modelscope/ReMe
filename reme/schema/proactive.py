"""Proactive refresh schemas.

Defines the topic model (v2), the chain-shared context state, and the
``daily/_proactive.yaml`` truth-source file model. The LLM reply contract is
validated structurally by ``parse_extract_reply`` instead of a model here.
See ``PROACTIVE_SPEC.md`` sections F1/A2 for the full contracts.
"""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Topic kinds, ordered by proactive priority: ``reminder`` outranks the rest
# and pins today's agenda, ``interest_extend`` is the lowest-priority
# discovery kind. ``KIND_PRIORITY`` is the single ordering source used by
# ``sort_topics`` and by the plan/agenda steps.
TOPIC_KINDS = ("reminder", "follow_up", "new_idea", "interest_extend")
KIND_PRIORITY = {kind: index for index, kind in enumerate(TOPIC_KINDS)}
DEFAULT_KIND = "interest_extend"

# Reminder registry (``daily/_proactive.yaml: schedules``) vocabularies. The
# registry outlives ``open_topics`` because a schedule mentioned weeks ago
# still has to fire on its due date.
SCHEDULE_ACTIONS = ("add", "reschedule", "confirm", "done", "cancel")
SCHEDULE_STATUSES = ("open", "done", "cancelled")
RECURRENCES = ("", "daily", "weekly", "monthly", "yearly")
REMINDER_TRIGGERS = ("overdue", "due_today", "due_soon", "conflict")

# Keys inside the untyped ``history`` audit trail that hold a date/datetime.
HISTORY_WHEN_KEYS = ("at", "from", "to")


def clamp_confidence(value) -> float:
    """Coerce confidence into [0, 1]; any conversion failure falls back to 0.5."""
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def iso_text(value) -> str:
    """Coerce a YAML-native scalar into the ISO text the string fields expect.

    ``yaml.safe_load`` reads an unquoted ``2026-10-11`` as ``datetime.date`` and
    ``2026-10-11T20:00`` as ``datetime.datetime``. The truth source is a
    hand-editable file and the schedule registry is meant to outlive topics by
    months, so a bare date must never invalidate an entry: date and time
    scalars are rendered back to ISO text, anything else falls back to ``str``.
    """
    if value is None:
        return ""
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def kind_priority(kind) -> int:
    """Priority rank of a topic kind; unknown kinds sort last."""
    return KIND_PRIORITY.get(str(kind or "").strip(), len(TOPIC_KINDS))


class ProactiveTopic(BaseModel):
    """One proactive topic; every field has a default so v1 files parse seamlessly.

    Fallback rules (A2): invalid ``kind`` -> ``interest_extend``; unparseable
    ``confidence`` -> 0.5. Missing ``id``, ``first_seen`` and
    ``last_evidence_at`` are context-dependent and therefore resolved by the
    loaders, not here.
    """

    id: str = ""
    title: str = ""
    reason: str = ""
    kind: str = DEFAULT_KIND
    confidence: float = 0.5
    first_seen: str = ""
    last_evidence_at: str = ""
    evidence: str = ""
    paths: list[str] = Field(default_factory=list)
    # Reminder-only links: ``schedule_id`` points at the long-lived registry
    # entry, ``due_at`` is the ISO date/datetime the reminder is about.
    schedule_id: str = ""
    due_at: str = ""

    @field_validator("kind", mode="before")
    @classmethod
    def _fallback_kind(cls, value):
        text = str(value or "").strip()
        return text if text in TOPIC_KINDS else DEFAULT_KIND

    @field_validator("confidence", mode="before")
    @classmethod
    def _fallback_confidence(cls, value):
        return clamp_confidence(value)

    @field_validator("first_seen", "last_evidence_at", "due_at", mode="before")
    @classmethod
    def _iso_when(cls, value):
        return iso_text(value)

    @field_validator("paths", mode="before")
    @classmethod
    def _clean_str_list(cls, value):
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ProactiveSchedule(BaseModel):
    """One personal schedule/appointment in the long-lived reminder registry.

    The registry is a separate truth-source section from ``open_topics``: a
    schedule survives topic trimming (``carry_forward_days``) until its due
    date has passed by ``schedule_retention_days``, and every change the
    pipeline observes is appended to ``history`` so a reschedule or a
    cancellation stays auditable long after the originating daily note left
    the extract scan window.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    detail: str = ""
    due_at: str = ""
    due_end_at: str = ""
    recurrence: str = ""
    # 0 = "not specified": the reminder scan then applies the step-level
    # ``reminder_lead_days`` default instead of a per-schedule value.
    lead_days: int = 0
    status: str = "open"
    confidence: float = 0.5
    first_seen: str = ""
    last_seen_at: str = ""
    evidence: str = ""
    paths: list[str] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def _fallback_status(cls, value):
        text = str(value or "").strip()
        return text if text in SCHEDULE_STATUSES else "open"

    @field_validator("recurrence", mode="before")
    @classmethod
    def _fallback_recurrence(cls, value):
        text = str(value or "").strip().lower()
        return text if text in RECURRENCES else ""

    @field_validator("due_at", "due_end_at", "first_seen", "last_seen_at", mode="before")
    @classmethod
    def _iso_when(cls, value):
        return iso_text(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _fallback_confidence(cls, value):
        return clamp_confidence(value)

    @field_validator("lead_days", mode="before")
    @classmethod
    def _fallback_lead_days(cls, value):
        try:
            return max(0, min(int(value), 365))
        except (TypeError, ValueError):
            return 0

    @field_validator("paths", mode="before")
    @classmethod
    def _clean_str_list(cls, value):
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("history", mode="before")
    @classmethod
    def _clean_history(cls, value):
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                continue
            cleaned.append({k: iso_text(v) if k in HISTORY_WHEN_KEYS else v for k, v in item.items()})
        return cleaned


class ProactiveState(BaseModel):
    """Chain-shared proactive context state (``context['proactive']``).

    Extract fills change-detection/carry-forward/LLM output fields; topics fills the
    filtering fields plus ``push_candidates`` (today's pushable topics); plan
    expands candidates into ``scenario_cards``; agenda selects the ordered
    ``agenda`` and records ``suppressed`` candidates with reasons; finish
    records the catalog checkpoint. ``plan_llm_calls`` counts plan+agenda LLM
    calls separately from extract's ``llm_calls``.
    ``file_skip_reason`` is metadata/log only and never persisted to
    interests.yaml (v5 simplification R7).
    """

    date: str = ""
    daily_dir: str = "daily"
    workspace: str = ""
    scan_days: int = 2
    carry_forward_days: int = 14
    changed_paths: list[str] = Field(default_factory=list)
    changed_mtimes: dict[str, float] = Field(default_factory=dict)
    # External source records (``resource/``) scanned for user-facing notices.
    # They feed the reminder branch only, but share ``changed_mtimes`` and the
    # proactive catalog watermark with the daily material set, so a notice that
    # lands on a day without any conversation still triggers a round.
    resource_scanned: int = 0
    resource_skipped: int = 0
    resource_changed: list[str] = Field(default_factory=list)
    carry_forward_count: int = 0
    carry_forward_prompt: list[ProactiveTopic] = Field(default_factory=list)
    llm_calls: int = 0
    follow_ups: list[dict] = Field(default_factory=list)
    extends: list[dict] = Field(default_factory=list)
    reminders: list[dict] = Field(default_factory=list)
    new_ideas: list[dict] = Field(default_factory=list)
    updates: list[dict] = Field(default_factory=list)
    schedule_updates: list[dict] = Field(default_factory=list)
    # Stage-2 adjudication (precision pass over stage-1 candidates). Every
    # failure is fail-open, so ``refine_degraded`` counts the kinds whose
    # stage-1 candidates were kept untouched.
    refine_calls: int = 0
    refine_degraded: int = 0
    refine_dropped: list[dict] = Field(default_factory=list)
    refine_moved: list[dict] = Field(default_factory=list)
    early_exit: str = ""
    # ``reminder_only`` marks a clock-driven round with no new material: the
    # chain stays alive (no ``early_exit``) but made zero LLM calls.
    reminder_only: bool = False
    due_schedules: list[dict] = Field(default_factory=list)
    updates_applied: int = 0
    updates_resolved: int = 0
    schedules_added: int = 0
    schedules_updated: int = 0
    schedules_closed: int = 0
    # Reminders whose published due value was re-read from the registry because
    # this round's ``schedule_updates`` moved it after the clock scan.
    reminders_reanchored: int = 0
    schedules_out: list[dict] = Field(default_factory=list)
    candidates_in: int = 0
    candidates: list[dict] = Field(default_factory=list)
    dropped_missing: int = 0
    dropped_duplicate: int = 0
    dropped_known: int = 0
    dropped_over_cap: int = 0
    topics_out: list[dict] = Field(default_factory=list)
    push_candidates: list[dict] = Field(default_factory=list)
    scenario_cards: list[dict] = Field(default_factory=list)
    agenda: list[dict] = Field(default_factory=list)
    suppressed: list[dict] = Field(default_factory=list)
    plan_llm_calls: int = 0
    push: bool = False
    file_skip_reason: str = ""
    interests_path: str = ""
    interests_written: bool = False
    checkpoint_paths: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class ProactiveStateFile(BaseModel):
    """On-disk truth-source ``daily/_proactive.yaml`` (F1.3, v5: 3 sections).

    ``resolved`` tombstones carry ``first_seen`` so a resurrected topic can
    keep its original age anchor (F2.4 reopen channel).
    ``schedules`` is the long-lived reminder registry; it is optional so
    files written before the reminder branch existed still load.
    """

    model_config = ConfigDict(extra="ignore")

    version: int = 1
    open_topics: list[ProactiveTopic] = Field(default_factory=list)
    resolved: list[dict] = Field(default_factory=list)
    schedules: list[ProactiveSchedule] = Field(default_factory=list)


class ProactiveResult(BaseModel):
    """Result of reading daily interest topics (F5)."""

    date: str = ""
    path: str = ""
    topics: list[dict] = Field(default_factory=list)
    content: str = ""
    skipped: bool = False
    error: str = ""
    summary: str = ""
    push: bool | None = None
    generated_at: str = ""
    agenda: list[dict] = Field(default_factory=list)
