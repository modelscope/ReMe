"""Replay strict grades and diagnose formatting separately from factual content retention."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import statistics

from benchmark.compaction.hybrid_cases import evaluate
from benchmark.compaction.run import exact_match, write


def canonical(value, expected, key=""):  # pylint: disable=too-many-return-statements
    """Normalize only explicit number/boolean spellings and an unambiguous source-line notation."""
    if type(expected) is int and not isinstance(value, bool):
        if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
            return int(value.strip())
        if isinstance(value, float) and math.isfinite(value) and value.is_integer():
            return int(value)
        if key == "key_generation_line" and isinstance(value, str):
            match = re.fullmatch(
                r"(?:retry\.py(?::\s*|\s+line\s+)|line\s+|L)([0-9]+)",
                value.replace("`", "").strip(),
                re.IGNORECASE,
            )
            if match:
                return int(match.group(1))
    if type(expected) is bool and isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    if isinstance(expected, dict) and isinstance(value, dict):
        return {k: canonical(v, expected.get(k), k) for k, v in value.items()}
    if isinstance(expected, list) and isinstance(value, list) and len(value) == len(expected):
        value = [canonical(v, e) for v, e in zip(value, expected)]
        return sorted(value, key=str) if key == "no_retry_http_statuses" else value
    return value


def content_checks(case, answer):
    """Post-hoc secondary metric; the frozen strict grades are never overwritten."""
    observed = answer.get("facts", {}) if isinstance(answer, dict) else {}
    observed = observed if isinstance(observed, dict) else {}
    return {key: exact_match(canonical(observed.get(key), value, key), value) for key, value in case["gold"].items()}


def analyze(directory):
    """Recompute each valid answer, retaining invalid compression counts in the denominators."""
    rows = json.loads((directory / "results.json").read_text())
    groups, formats, audited = {}, Counter(), 0
    for row in rows:
        groups.setdefault((row["case"], row["budget"], row["arm"]), []).append(row)
        if row["valid"]:
            case = json.loads((directory / f"{row['case']}.source.json").read_text())
            for trial in row["trials"]:
                assert evaluate(case, trial["answer"]) == trial["checks"]
                secondary = content_checks(case, trial["answer"])
                trial["content_checks"] = secondary
                formats.update(key for key, okay in secondary.items() if okay and not trial["checks"]["facts"][key])
                audited += 1
    result = []
    for (case, budget, arm), group in groups.items():
        valid = [r for r in group if r["valid"]]
        trials = [t for r in valid for t in r["trials"]]
        row = {
            "case": case,
            "budget": budget,
            "arm": arm,
            "valid_compressions": len(valid),
            "compressions": len(group),
        }
        if trials:
            row.update(
                {
                    "strict_fact_accuracy": statistics.mean(
                        sum(t["checks"]["facts"].values()) / len(t["checks"]["facts"]) for t in trials
                    ),
                    "content_fact_accuracy": statistics.mean(
                        sum(t["content_checks"].values()) / len(t["content_checks"]) for t in trials
                    ),
                    "strict_all_facts": statistics.mean(all(t["checks"]["facts"].values()) for t in trials),
                    "content_all_facts": statistics.mean(all(t["content_checks"].values()) for t in trials),
                    "task_success": statistics.mean(all(t["checks"]["task"].values()) for t in trials),
                    "prompt_tokens": statistics.mean(t["usage"]["prompt_tokens"] for t in trials),
                },
            )
            row["effective_all_facts"] = row["content_all_facts"] * len(valid) / len(group)
        result.append(row)
    return rows, result, {"replayed_answers": audited, "format_only_mismatches": dict(formats)}


def pairs(rows):
    """Compare appended contexts against their own exact baseline generation, not another summary."""
    baselines = {(r["case"], r["budget"], r["compression_repeat"]): r for r in rows if r["arm"] == "same_summary"}
    paired = {}
    for row in rows:
        if row["arm"] == "same_summary" or not row["valid"]:
            continue
        base = baselines[(row["case"], row["budget"], row["compression_repeat"])]
        if not base["valid"]:
            continue
        assert base["summary_sha256"] == row["summary_sha256"]
        for metric in ["strict", "content"]:

            def accuracy(item, scoring=metric):
                """Average one fixed generation under the selected scoring rule."""
                return statistics.mean(
                    (
                        sum(t["checks"]["facts"].values()) / len(t["checks"]["facts"])
                        if scoring == "strict"
                        else sum(t["content_checks"].values()) / len(t["content_checks"])
                    )
                    for t in item["trials"]
                )

            difference = accuracy(row) - accuracy(base)
            key = row["arm"] + "." + metric
            paired.setdefault(key, []).append(difference)
    return {
        key: {
            "n": len(values),
            "mean_delta_points": statistics.mean(values) * 100,
            "improved": sum(d > 1e-9 for d in values),
            "tied": sum(abs(d) <= 1e-9 for d in values),
            "worsened": sum(d < -1e-9 for d in values),
        }
        for key, values in paired.items()
    }


def main():
    """Analyze saved artifacts only; no model calls or source artifact rewrites."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--incremental", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--aware", type=Path)
    args = parser.parse_args()
    _, primary, primary_audit = analyze(args.primary)
    incremental_rows, incremental, incremental_audit = analyze(args.incremental)
    result = {
        "primary": primary,
        "incremental": incremental,
        "paired": pairs(incremental_rows),
        "audits": {"primary": primary_audit, "incremental": incremental_audit},
        "secondary_scope": "Post-hoc format normalization, separate from frozen strict scoring",
    }
    if args.aware:
        aware_rows, aware, aware_audit = analyze(args.aware)
        result.update({"summary_aware": aware, "aware_paired": pairs(aware_rows)})
        result["audits"]["summary_aware"] = aware_audit
    write(args.output, result)


if __name__ == "__main__":
    main()
