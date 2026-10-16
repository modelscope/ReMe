"""Gold scoring, leakage boundaries and complete-input budgeting without provider calls."""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from benchmark.compaction.cases import choose, evaluate, event_units, fixture, normalize, render
from benchmark.compaction.run import Experiment, aggregate, compose, decision_input, messages, select


class CharacterTokenizer:
    """Use character counts to exercise exact budget boundaries deterministically."""

    @staticmethod
    def encode(text, **_kwargs):
        """Expose the tokenizer count interface without external assets."""
        return SimpleNamespace(ids=list(text))


def example():
    """Provide two-hop gold independently of the prediction under test."""
    return {"gold": {"answer": "The Nile", "supporting_facts": [["Egypt", 0], ["Nile", 2]]}}


def test_official_answer_normalization_and_boolean_answers():
    """Normalize punctuation/articles while preserving categorical yes/no semantics."""
    case = example()
    assert normalize("  The NILE! ") == "nile"
    check = evaluate(case, {"answer": "Nile", "supporting_facts": [["Nile", 2], ["Egypt", 0]]})
    assert check["metrics"]["answer_em"] == check["metrics"]["joint_em"] == 1
    case["gold"]["answer"] = "yes"
    assert evaluate(case, {"answer": "yes indeed"})["metrics"]["answer_f1"] == 0
    assert evaluate(case, {"answer": "no"})["metrics"]["answer_f1"] == 0


def test_partial_answers_and_missing_support_do_not_receive_joint_credit():
    """Exact answer and complete supporting facts are separate requirements."""
    case = example()
    case["gold"]["answer"] = "Lake Victoria"
    result = evaluate(case, {"answer": "Victoria", "supporting_facts": [["Egypt", 0]]})["metrics"]
    assert result["answer_em"] == 0 and result["answer_f1"] == pytest.approx(2 / 3)
    assert result["support_f1"] == pytest.approx(2 / 3) and result["joint_em"] == 0


@pytest.mark.parametrize("index", [True, 2.0, "2"])
def test_supporting_sentence_ids_require_integers(index):
    """Python equality must not silently give booleans/floats the identity of an integer ID."""
    result = evaluate(example(), {"answer": "Nile", "supporting_facts": [["Egypt", 0], ["Nile", index]]})
    assert result["metrics"]["answer_em"] == 1 and result["metrics"]["support_em"] == 0
    assert result["metrics"]["joint_em"] == 0


def test_duplicate_supports_are_sets_and_invalid_predictions_score_zero():
    """Duplicate citations cannot inflate recall; malformed answers remain failures."""
    case = example()
    assert evaluate(case, [])["metrics"]["answer_em"] == 0
    result = evaluate(case, {"answer": "Nile", "supporting_facts": [["Egypt", 0], ["Egypt", 0], ["Nile", 2]]})
    assert result["metrics"]["joint_em"] == 1


def test_fixture_exposes_articles_and_question_without_gold():
    """Gold labels exist before collection but cannot enter the agent's file workspace."""
    row = {
        "question": "Which river?",
        "answer": "HIDDEN_GOLD",
        "supporting_facts": [["Nile", 2]],
        "context": [["Nile", ["It crosses Egypt."]]],
    }
    prompt, files = fixture(row)
    assert "HIDDEN_GOLD" not in prompt + json.dumps(files)
    assert "supporting_facts" not in json.dumps(files)
    assert "sentence 0: It crosses Egypt." in files["article-00.txt"]


def test_sampling_is_frozen_balanced_and_article_disjoint():
    """Selection depends on the corpus/seed and structural eligibility, never model outcomes."""
    rows = []
    for i in range(10):
        title = f"article-{i}"
        rows.append(
            {
                "_id": str(i),
                "question": "question",
                "answer": "gold",
                "type": "bridge" if i % 2 else "comparison",
                "supporting_facts": [[title, 0]],
                "context": [[f"article-{i}-{j}" if j else title, ["x" * 650]] for j in range(10)],
            },
        )
    before = deepcopy(rows)
    picked = choose(rows, count=4)
    assert picked == choose(list(reversed(rows)), count=4)
    assert sum(r["type"] == "bridge" for r in picked) == 2
    titles = [title for r in picked for title, _ in r["context"]]
    assert len(titles) == len(set(titles)) == 40 and rows == before
    with pytest.raises(ValueError):
        choose(rows, count=3)


def test_sentence_units_reconstruct_every_original_character():
    """Grouping retains article title, original sentence IDs and exact source ranges."""
    text = "1|title: River\n2|sentence 0: Fact A.\n3|sentence 1: Fact B.\n"
    history = [
        {"role": "assistant", "tool_calls": [{"id": "c", "function": {"arguments": '{"path":"a.txt"}'}}]},
        {"role": "tool", "tool_call_id": "c", "content": json.dumps({"content": text})},
    ]
    before = deepcopy(history)
    units = event_units(history)
    assert "".join(u["text"] for u in units) == text
    assert all(u["title"] == "River" for u in units)
    assert all(text[s["start"] : s["end"]] == s["text"] for u in units for s in u["spans"])
    assert history == before
    assert "sentence 1" in render(units)


def test_ranked_selection_restores_source_order_and_keeps_whole_units():
    """Higher ranking determines retention but cannot rearrange or truncate source text."""
    units = [{"id": str(i), "file": "x", "spans": [{"start": i, "end": i + 1}], "text": "abc"} for i in range(3)]
    limit = len(render([units[0], units[2]]))
    assert select(units, {"0": 0.8, "1": 0.1, "2": 0.9}, lambda raw: len(raw) <= limit) == [units[0], units[2]]


def test_complete_input_ceiling_includes_protected_context_and_exam(tmp_path):
    """The last byte of available capacity is shared by all three compressed methods."""
    case = {
        "messages": [{"role": "system", "content": "S" * 100}, {"role": "user", "content": "task"}],
        "exam": "E" * 100,
    }
    exp = Experiment(None, None, tmp_path, CharacterTokenizer(), asyncio.Semaphore(1), "mock", 10000)
    payload = compose("summary", "evidence")
    exp.cap = exp.input_tokens(messages(case, payload)) + 64
    assert exp.fits(case, payload) and not exp.fits(case, payload + "x")
    assert messages(case) == [*case["messages"], {"role": "user", "content": case["exam"]}]


def test_decision_inputs_contain_source_title_but_no_gold_or_exam():
    """Citation identity is visible to selection without exposing scoring labels."""
    state, questions = decision_input("task", [{"id": "u", "file": "log", "title": "River", "text": "event"}])
    assert set(state) == {"task", "evidence_units"}
    assert state["evidence_units"][0]["title"] == "River"
    assert "continue the task" in questions["u"]["instructions"]
    assert "gold" not in json.dumps(state) and "exam" not in json.dumps(state)


def test_failed_conditions_stay_in_denominator():
    """Model/budget failures cannot disappear when computing accuracy."""
    rows = [
        {"case": "x", "arm": "summary", "valid": False, "trials": []},
        {
            "case": "x",
            "arm": "summary",
            "valid": True,
            "trials": [
                {
                    "checks": {"facts": {"a": 1}, "task": {"b": 1}, "metrics": {"answer_em": 1}},
                    "usage": {"prompt_tokens": 100},
                },
            ],
        },
    ]
    row = next(r for r in aggregate(rows) if r["arm"] == "summary")
    assert row["valid"] == 1 and row["attempted"] == 2
    assert row["answer_em"] == row["facts"] == row["task"] == 0.5


def test_fusion_summary_sees_both_evidence_partitions_without_gold(tmp_path):
    """Exercise real packing and composition while mocking only provider boundaries."""
    captured = []

    class FakeExperiment(Experiment):
        """Expose the summary's actual request and reject no valid input."""

        async def scores(self, _label, _task, _units):
            """Keep just the first source group verbatim."""
            return {"u1": 0.9, "u2": 0.1}, []

        async def ask(self, _label, context, *, summary=False):
            """Return finite deterministic summary/answer responses."""
            captured.append((summary, context))
            return ("Complementary summary." if summary else '{"answer":"Nile","supporting_facts":[]}'), {
                "prompt_tokens": 900,
            }

    case = {
        **example(),
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "task"},
        ],
        "exam": "HIDDEN_EXAM",
    }
    units = [
        {"id": f"u{i}", "file": "article", "text": f"event-{i}", "spans": [{"start": i, "end": i + 1}]} for i in (1, 2)
    ]
    row = {"case": "case", "repeat": 0, "arm": "fusion"}
    exp = FakeExperiment(None, None, tmp_path, CharacterTokenizer(), asyncio.Semaphore(1), "mock", 1000)
    asyncio.run(exp.condition(row, case, units, 1))
    assert row["valid"] and row["selected"] == ["u1"]
    requests = [context for summary, context in captured if summary]
    supplied = json.loads(requests[0][1]["content"])
    assert supplied["retained_evidence"] == units[:1] and supplied["remaining_evidence"] == units[1:]
    assert "HIDDEN_" not in json.dumps(requests) and "gold" not in json.dumps(supplied)


def test_corpus_projection_removes_hermes_db_metadata_and_verifies_hashes(tmp_path):
    """Only real chat fields may affect model inputs; immutable raw session exports stay intact."""
    import hashlib

    from benchmark.compaction.cases import dataset, write

    root = tmp_path / "task"
    root.mkdir()
    source = {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "question", "_db_row_snapshot": {"content": "INTERNAL_COPY"}},
            {"role": "assistant", "content": "final answer", "reasoning": "PRIVATE_INTERNAL"},
        ],
    }
    write(root / "trajectory.full.json", source)
    before = (root / "trajectory.full.json").read_bytes()
    write(root / "collection.json", {"completed": True, "trajectory_sha256": hashlib.sha256(before).hexdigest()})
    write(tmp_path / "collection-status.json", {"completed": 1, "failed": []})
    write(
        tmp_path / "corpus.json",
        {"questions": [{"_id": "task", "type": "bridge", "answer": "gold", "supporting_facts": [["A", 0]]}]},
    )
    result = dataset(tmp_path / "corpus.json")
    assert result["task"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "question"},
    ]
    assert "INTERNAL_COPY" not in json.dumps(result) and "PRIVATE_INTERNAL" not in json.dumps(result)
    assert (root / "trajectory.full.json").read_bytes() == before
    (root / "trajectory.full.json").write_text("{}")
    with pytest.raises(ValueError, match="modified"):
        dataset(tmp_path / "corpus.json")
