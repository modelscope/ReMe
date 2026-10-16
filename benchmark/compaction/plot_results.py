"""Render the frozen long-log comparison as a documentation SVG using optional Matplotlib."""

import argparse
import json
from pathlib import Path


def plot(results, output):
    """Show all four arms at the 1000-token evidence allowance without truncating axes."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    rows = {
        row["arm"]: row
        for row in results
        if row["scenario"] == "long_log_control" and row.get("valid") and row["budget"] in (None, 1000)
    }
    arms = ["full", "jev_spans", "head_tail", "llm_summary"]
    labels = ["Full evidence", "Jev spans", "Head/tail", "LLM summary"]
    colors = ["#94a3b8", "#2563eb", "#e6a23c", "#0d9488"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "reme-compaction-benchmark",
        },
    )
    figure, axes = plt.subplots(1, 3, figsize=(15, 7))
    figure.patch.set_facecolor("#ffffff")
    figure.subplots_adjust(left=0.09, right=0.97, top=0.70, bottom=0.30, wspace=0.63)
    figure.text(0.04, 0.92, "Context compaction: long-log comparison", size=23, weight="bold", color="#0f172a")
    figure.text(
        0.04,
        0.86,
        "Same task. Same protected context. 1,000-token evidence allowance.",
        size=12,
        color="#475569",
    )
    configurations = [
        ("Total input tokens", "Lower is better", [rows[a]["prompt_tokens"] for a in arms], 10500),
        ("Fact accuracy", "Higher is better", [100 * rows[a]["fact_accuracy"] for a in arms], 119),
        (
            "Compaction time",
            "Lower is better",
            [
                None,
                rows["jev_spans"]["compression"]["seconds"],
                None,
                rows["llm_summary"]["compression"]["seconds"],
            ],
            20,
        ),
    ]
    for index, (axis, (title, direction, values, ceiling)) in enumerate(zip(axes, configurations)):
        axis.set_title(title + "\n" + direction, loc="left", fontsize=12, fontweight="bold", pad=20, color="#0f172a")
        axis.set_xlim(0, ceiling)
        axis.set_ylim(3.6, -0.65)
        axis.set_yticks(range(4), labels, fontsize=10)
        axis.tick_params(axis="both", length=0, colors="#475569", pad=8)
        axis.set_axisbelow(True)
        axis.grid(axis="x", color="#e2e8f0", linewidth=0.8)
        for spine in axis.spines.values():
            spine.set_visible(False)
        for y, value in enumerate(values):
            if value is None:
                axis.text(0, y, "Not measured", va="center", fontsize=10, color="#94a3b8")
                continue
            axis.barh(y, value, height=0.48, color=colors[y], zorder=3)
            formatted = f"{value:,.0f}" if index == 0 else f"{value:.0f}%" if index == 1 else f"{value:.2f} s"
            axis.text(value + ceiling * 0.025, y, formatted, va="center", fontsize=10, color="#0f172a")
        if index == 0:
            axis.set_xticks([0, 3000, 6000, 9000], ["0", "3k", "6k", "9k"])
        elif index == 1:
            axis.set_xticks([0, 50, 100])
            axis.xaxis.set_major_formatter(PercentFormatter())
        else:
            axis.set_xticks([0, 5, 10, 15], ["0 s", "5 s", "10 s", "15 s"])
    reduction = 100 * (1 - rows["jev_spans"]["prompt_tokens"] / rows["full"]["prompt_tokens"])
    figure.text(
        0.04,
        0.23,
        f"Jev: {reduction:.1f}% fewer input tokens than full evidence.",
        size=13,
        weight="bold",
        color="#2563eb",
    )
    figure.text(
        0.04,
        0.18,
        "Jev is faster in this run; the summary retains more facts (90% vs. 85%).",
        size=12,
        color="#334155",
    )
    figure.text(
        0.04,
        0.11,
        "One synthetic payment task with added routine logs; two answers per context. "
        "All arms pass all six repair tests.",
        size=10,
        color="#64748b",
    )
    figure.text(
        0.04,
        0.07,
        "Budget: local Qwen tokenizer proxy. Input: API usage. "
        "Latency: one local compaction measurement. No archive retrieval.",
        size=10,
        color="#64748b",
    )
    figure.text(
        0.04,
        0.03,
        "Run: 2026-10-15 | Qwen: qwen3.8-max | Jev: jev-1.13.0 | "
        "Protocol and results: benchmark/compaction/RESULTS.md",
        size=9,
        color="#64748b",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output,
        format=output.suffix.lstrip("."),
        metadata={"Date": "2026-10-15", "Title": "Long-log compaction comparison"},
    )
    if output.suffix == ".svg":
        lines = output.read_text(encoding="utf-8").splitlines()
        output.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
    plt.close(figure)


def plot_hybrid(results, output, *, incremental=False, aware=False):
    """Show every fixed allocation and budget, with separate case rows and a common zero-based scale."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    arms = ["summary", "spans", "head_tail", "hybrid70", "hybrid50", "hybrid30", "rule_hybrid50"]
    labels = ["Summary", "Jev", "Head/tail", "S70/E30", "S50/E50", "S30/E70", "Rule 50/50"]
    cases = ["payment_short", "payment_long", "replica"]
    names = ["Payment / short", "Payment / long", "Replica fixture"]
    budgets = [600, 1000, 1600]
    metrics = ["fact_accuracy", "all_facts"]
    titles = ["Mean fact accuracy", "All facts correct"]
    title = "Summary + exact evidence: the full comparison"
    subtitle = "Direct Qwen evaluation | Two compression generations x two answers | S = summary; E = original evidence"
    if incremental:
        arms = ["same_summary", "jev200", "jev400", "recency400"]
        labels = ["Same summary", "+ Jev 200", "+ Jev 400", "+ Rule 400"]
        budgets = [300, 600, 1000]
        metrics = ["strict_fact_accuracy", "content_fact_accuracy"]
        titles = ["Strict field accuracy", "Content match (format-normalized)"]
        title = "Keep the summary. Append original evidence."
        subtitle = (
            "Direct Qwen evaluation | Same summary bytes in every comparison | "
            "Added input tokens are reported separately"
        )
    if aware:
        arms = ["same_summary", "goal_gated400", "aware400"]
        labels = ["Same summary", "+ Goal-only", "+ Summary-aware"]
        title = "Select what the summary is missing."
        subtitle = (
            "Same frozen summary | Both selectors: probability >= 0.5, at most 400 evidence tokens | "
            "Total input increases"
        )
    indexed = {(row["case"], row["budget"], row["arm"]): row for row in results}
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.fonttype": "none",
            "svg.hashsalt": "reme-compaction-hybrid",
        },
    )
    figure, axes = plt.subplots(1, 2, figsize=(17, 8), sharey=True)
    figure.subplots_adjust(left=0.12, right=0.94, top=0.77, bottom=0.26, wspace=0.13)
    figure.text(0.04, 0.94, title, size=23, weight="bold", color="#0f172a")
    figure.text(
        0.04,
        0.89,
        subtitle,
        size=12,
        color="#475569",
    )
    row_labels = []
    for name in names:
        row_labels += [f"{name} / {budget}" for budget in budgets]
    for axis, metric, title in zip(axes, metrics, titles):
        values = np.full((9, len(arms)), np.nan)
        for ci, case in enumerate(cases):
            for bi, budget in enumerate(budgets):
                for ai, arm in enumerate(arms):
                    row = indexed.get((case, budget, arm))
                    if row and row["valid_compressions"]:
                        value = row[metric] * 100
                        values[ci * 3 + bi, ai] = value
                        label = f"{value:.0f}%" if abs(value - round(value)) < 1e-8 else f"{value:.1f}%"
                        label += "*" if row["valid_compressions"] < row["compressions"] else ""
                        axis.text(
                            ai,
                            ci * 3 + bi,
                            label,
                            ha="center",
                            va="center",
                            color="white" if value > 65 else "#0f172a",
                            fontsize=10,
                        )
                    else:
                        axis.text(ai, ci * 3 + bi, "Invalid", ha="center", va="center", color="#64748b", fontsize=9)
        heat = axis.imshow(values, cmap="Blues", vmin=0, vmax=100, aspect="auto")
        axis.set_title(title, loc="left", size=14, weight="bold", pad=16)
        axis.set_xticks(range(len(arms)), labels, rotation=35, ha="right")
        axis.set_yticks(range(9), row_labels)
        axis.tick_params(length=0, pad=8)
        for y in [2.5, 5.5]:
            axis.axhline(y, color="white", linewidth=4)
        for spine in axis.spines.values():
            spine.set_visible(False)
    color_axis = figure.add_axes([0.955, 0.26, 0.012, 0.51])
    figure.colorbar(heat, cax=color_axis, ticks=[0, 25, 50, 75, 100], format="%.0f%%")
    figure.text(
        0.04,
        0.16,
        (
            "Base summary allowances: 300 / 600 / 1,000 tokens. Evidence is appended; total input increases. "
            "Secondary content scoring normalizes only explicit formats."
            if incremental
            else "Budgets: 600 / 1,000 / 1,600 payload tokens, including labels and citations. "
            "Local tokenizer proxy; actual API usage recorded."
        ),
        size=11,
        color="#475569",
    )
    figure.text(
        0.04,
        0.11,
        "One payment task plus a noise variant and one independent replica fixture. "
        "No Hermes continuation or archive retrieval.",
        size=11,
        color="#64748b",
    )
    figure.text(
        0.04,
        0.06,
        "Each cell averages four answers when both compressions are valid. "
        "* = incomplete coverage; see valid/attempted counts in the report.",
        size=10,
        color="#64748b",
    )
    figure.text(
        0.04,
        0.02,
        "Run: 2026-10-16 | qwen3.8-max | Descriptive small-sample experiment, not evidence of general task success.",
        size=10,
        color="#64748b",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, format=output.suffix.lstrip("."), metadata={"Date": "2026-10-16"})
    if output.suffix == ".svg":
        output.write_text("\n".join(line.rstrip() for line in output.read_text().splitlines()) + "\n")
    plt.close(figure)


def main():
    """Read saved experiment results; plotting never calls model providers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--aware", action="store_true")
    args = parser.parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    if args.aware:
        plot_hybrid(results["summary_aware"], args.output, incremental=True, aware=True)
    elif args.incremental:
        plot_hybrid(results["incremental"], args.output, incremental=True)
    else:
        renderer = plot_hybrid if args.hybrid else plot
        renderer(results, args.output)


if __name__ == "__main__":
    main()
