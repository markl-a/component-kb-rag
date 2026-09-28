"""Offline evaluation: retrieval hit@k (right document cited), answer containment, and refusal on out-of-scope."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from kb.answer import KB
from kb.ingest import ingest

ROOT = Path(__file__).resolve().parent.parent


def evaluate() -> dict:
    kb = KB(ingest(ROOT / "docs"))
    qs = yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text())
    rows = []
    for item in qs:
        out = kb.ask(item["q"])
        cited = {s.split(":")[0] for s in out["sources"]}
        hit = (not item["expect"] and not cited) or bool(cited & set(item["expect"]))
        rows.append({"q": item["q"], "route": out["route"], "hit": hit, "contains": item["must_contain"].lower() in out["answer"].lower(),
                     "sources": out["sources"]})
    n = len(rows)
    return {"n": n, "citation_hit": round(sum(r["hit"] for r in rows) / n, 3),
            "answer_contains": round(sum(r["contains"] for r in rows) / n, 3),
            "routes": {r: sum(1 for x in rows if x["route"] == r) for r in ("table", "retrieval", "none")}, "rows": rows}


if __name__ == "__main__":
    rep = evaluate()
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))
    for r in rep["rows"]:
        if not (r["hit"] and r["contains"]):
            print("FAIL", r)
