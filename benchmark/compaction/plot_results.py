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


def main():
    """Read saved experiment results; plotting never calls model providers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(json.loads(args.results.read_text(encoding="utf-8")), args.output)


if __name__ == "__main__":
    main()
