"""Frozen hybrid-evaluation cases and deterministic grading; no provider calls."""

from copy import deepcopy
import json
import re

from benchmark.compaction.repair_check import repair_checks
from benchmark.compaction.run import GOLD, REPAIR, exact_match, grade, load_source
from benchmark.compaction.span_experiment import FOLLOW_UP, noisy_variant

REPLICA_GOLD = {
    "incident_id": "INC-6192",
    "region": "region-A",
    "slot": "replica-a",
    "term": 17,
    "event_ids": ["F001", "W002", "L003"],
    "event_times": ["10:00:01", "10:00:04", "10:04:59"],
    "restart_lsn": "0/7000000",
    "confirmed_lsn": "0/3000000",
    "gap_bytes": 67108864,
    "slot_active": False,
    "audit_ticket": "SYN-008",
    "quorum_healthy": True,
    "lag_limit_bytes": 33554432,
    "required_samples": 3,
}
REPLICA_PLAN = {
    "action": "resume_apply",
    "rollback": False,
    "evidence_event_ids": ["F001", "W002", "L003"],
    "required_checks": ["quorum", "slot_identity", "audit_ticket"],
    "success_condition": {"lag_bytes_lt": 33554432, "samples": 3},
}
REPLICA_EXAM = """Using only recorded evidence, return JSON {"facts": {...}, "plan": {...}}.
Do not use tools. Missing facts must be null. Do not execute operations.
Facts keys: incident_id, region, slot, term, event_ids (chronological), event_times (chronological),
restart_lsn, confirmed_lsn, gap_bytes (compute the absolute LSN offset gap as an integer),
slot_active (boolean), audit_ticket, quorum_healthy (boolean), lag_limit_bytes, required_samples.
Plan keys:
action: one of resume_apply, rollback, drop_slot, wait_only;
rollback: boolean;
evidence_event_ids: chronological IDs supporting this action;
required_checks: names of the mandatory pre-action checks, using quorum, slot_identity, audit_ticket, or disk_space;
success_condition: {"lag_bytes_lt": integer, "samples": integer} from the current policy.
Distinguish the active region-A incident from obsolete documentation. A plan is a proposal, not an execution."""


def replica_messages(system):
    """Create an explicit synthetic fixture, not a new agent-collected trajectory."""
    task = (
        "Investigate the current region-A replica-lag incident and propose the permitted recovery plan. "
        "Use current logs, replication-slot offsets, cluster health, audit approval and the current policy. "
        "Preserve exact event IDs and timestamps. Distinguish completed unrelated work and retired runbooks. "
        "No rollback or live operations are permitted; report a plan only."
    )
    logs = []
    events = {
        31: "10:00:01 trace_id=fl-17 event=F001 leader_switch term=17 incident=INC-6192 region=region-A\n",
        78: "10:00:04 trace_id=fl-17 event=W002 apply_paused slot=replica-a\n",
        127: "10:04:59 trace_id=fl-17 event=L003 lag_bytes=67108864\n",
    }
    for i in range(160):
        logs.append(f"noise-{i:03d}|healthcheck ok service=unrelated-cache latency_ms={i % 13 + 1}\n")
        if i in events:
            logs.append(events[i])
    files = {
        "completed_marketing.txt": "Completed marketing analysis; unrelated to replication.\n"
        + "".join(f"retired-campaign-{i:03d} clicks={i*3} status=closed\n" for i in range(80)),
        "incident.log": "".join(logs),
        "replication_slots.txt": "region=region-A slot=replica-a restart_lsn=0/7000000 "
        "confirmed_lsn=0/3000000 active=false\n",
        "cluster_health.json": json.dumps(
            {
                "region": "region-A",
                "healthy_voters": 3,
                "total_voters": 3,
                "leader_term": 17,
                "quorum_healthy": True,
            },
        ),
        "recovery_policy.md": "# Active region-A recovery policy\n"
        "For paused apply after a leader switch, propose resume_apply only after quorum, slot_identity and "
        "audit_ticket checks. Those are the three mandatory check names. Never rollback or drop a slot.\n"
        "The target slot is replica-a. Compute the absolute gap between its two LSN offsets.\n"
        "Recovery is successful after lag_bytes is strictly below 33554432 for 3 consecutive samples.\n"
        "Do not execute any operation during this investigation.\n",
        "audit.txt": "ticket=SYN-008 approved_region=region-A approved_action=resume_apply incident=INC-6192\n",
        "retired_runbook.md": "# RETIRED: region-Z incident from 2021, NOT the current region-A incident\n"
        "Old recommendation: rollback. Old slot=replica-z; old threshold=1048576; old ticket=OLD-009.\n"
        "This historical runbook is obsolete and must not guide the current investigation.\n",
    }
    messages = [deepcopy(system), {"role": "user", "content": task}]
    for i, (path, content) in enumerate(files.items()):
        call_id = f"replica-{i}"
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": json.dumps({"path": path}),
                            },
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": call_id, "content": json.dumps({"content": content})},
            ],
        )
    return messages


def cases(path):
    """Return two task families and one controlled payment noise augmentation."""
    payment = load_source(path)
    replica = replica_messages(payment[0])
    return {
        "payment_short": {
            "messages": payment,
            "exam": FOLLOW_UP,
            "gold": GOLD,
            "plan_gold": REPAIR,
            "family": "payment",
            "provenance": "Hermes-collected synthetic task; final report excluded",
        },
        "payment_long": {
            "messages": noisy_variant(payment),
            "exam": FOLLOW_UP,
            "gold": GOLD,
            "plan_gold": REPAIR,
            "family": "payment",
            "provenance": "Controlled 180-line noise augmentation of payment_short",
        },
        "replica": {
            "messages": replica,
            "exam": REPLICA_EXAM,
            "gold": REPLICA_GOLD,
            "plan_gold": REPLICA_PLAN,
            "family": "replica",
            "provenance": "New deterministic synthetic fixture, not an agent trajectory",
        },
    }


def add_group(groups, spans):
    """Add one ordinary source block to this observation's event groups."""
    if spans:
        groups[f"block-{len(groups)}"] = spans


def event_units(messages):
    """Group correlated log lines without stripping noise or using expected answers."""
    calls = {c["id"]: c for m in messages for c in m.get("tool_calls", [])}
    units = []
    for mi, message in enumerate(messages):
        if message["role"] != "tool":
            continue
        call = calls[message["tool_call_id"]]
        args = json.loads(call["function"]["arguments"])
        path = args.get("path") or args.get("file_path") or str(args)
        text = json.loads(message["content"])["content"]
        groups, offset, routine, routine_chars = {}, 0, [], 0

        if len(text) <= 1200:
            add_group(groups, [{"start": 0, "end": len(text), "text": text}])
        else:
            for line in text.splitlines(keepends=True):
                span = {"start": offset, "end": offset + len(line), "text": line}
                offset += len(line)
                match = re.search(r"\b(invoice|trace_id|request_id)=([A-Za-z0-9_.:-]+)", line)
                if match:
                    groups.setdefault(match.group(0), []).append(span)
                else:
                    if routine and routine_chars + len(line) > 600:
                        add_group(groups, routine)
                        routine, routine_chars = [], 0
                    routine.append(span)
                    routine_chars += len(line)
            add_group(groups, routine)
        for spans in sorted(groups.values(), key=lambda group: group[0]["start"]):
            units.append(
                {
                    "id": f"m{mi}_{spans[0]['start']}",
                    "file": path,
                    "spans": spans,
                    "text": "".join(span["text"] for span in spans),
                },
            )
    return units


def render(units):
    """Keep exact noncontiguous source offsets visible alongside verbatim selected text."""
    return "\n\n".join(
        f"[{u['id']} {u['file']} chars " + ",".join(f"{s['start']}:{s['end']}" for s in u["spans"]) + "]\n" + u["text"]
        for u in units
    )


def pack(units, order, budget, count):
    """Select only whole event groups, then restore their original order."""
    selected = set()
    by_id = {u["id"]: u for u in units}
    for unit_id in order:
        proposed = [u for u in units if u["id"] in selected or u["id"] == unit_id]
        if unit_id in by_id and count(render(proposed)) <= budget:
            selected.add(unit_id)
    return [u for u in units if u["id"] in selected]


def evaluate(case, answer):
    """Separate exact fact retention from function tests or structured procedure checks."""
    answer = answer if isinstance(answer, dict) else {}
    if case["family"] == "payment":
        checks = grade(answer)
        facts = {k.removeprefix("facts."): v for k, v in checks.items() if k.startswith("facts.")}
        task = repair_checks(answer.get("repair_code", ""))
    else:
        facts = answer.get("facts", {})
        facts = facts if isinstance(facts, dict) else {}
        facts = {k: exact_match(facts.get(k), v) for k, v in REPLICA_GOLD.items()}
        plan = answer.get("plan", {})
        plan = plan if isinstance(plan, dict) else {}
        task = {
            k: (
                exact_match(sorted(plan.get(k, [])), sorted(v))
                if k == "required_checks" and isinstance(plan.get(k), list)
                else exact_match(plan.get(k), v)
            )
            for k, v in REPLICA_PLAN.items()
        }
    return {"facts": facts, "task": task}
