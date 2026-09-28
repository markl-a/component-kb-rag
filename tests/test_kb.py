from pathlib import Path

from eval.run_eval import evaluate
from kb.answer import KB
from kb.ingest import ingest

ROOT = Path(__file__).resolve().parent.parent
KBASE = KB(ingest(ROOT / "docs"))


def test_tables_become_structured_rows():
    rows = [r for r in KBASE.c.params if r["part"] == "AS60R045" and r["current"]]
    assert {r["parameter"] for r in rows} >= {"V_DS", "R_DS(on) max", "Q_g typical"}


def test_superseded_revision_is_not_used():
    out = KBASE.ask("What is the gate charge of AS60R045?")
    assert "68" in out["answer"] and "75" not in out["answer"] and "rev2" in out["sources"][0]


def test_part_number_spelling_variants():
    for q in ("as60r045 rds", "AS-60R045 on resistance", "AS60R045 RDS(on)"):
        assert KBASE.ask(q)["route"] == "table"


def test_pcn_questions_are_filtered_to_pcn_docs():
    out = KBASE.ask("When is the last time buy for AS60R070?")
    assert all(s.startswith("PCN-") for s in out["sources"]) and "2026-12-31" in out["answer"]


def test_out_of_scope_is_refused():
    out = KBASE.ask("What is the price of AS60R045?")
    assert out["route"] == "none" and out["sources"] == []


def test_eval_thresholds():
    rep = evaluate()
    assert rep["citation_hit"] >= 0.9 and rep["answer_contains"] >= 0.9, [r for r in rep["rows"] if not (r["hit"] and r["contains"])]
