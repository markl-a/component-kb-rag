"""Answer = structured lookup first, retrieval second, 'not found' last. Every answer carries its sources."""
from __future__ import annotations

import re

from .ingest import Corpus
from .retrieve import Retriever, normalize_pn

PARAM_ALIASES = {
    "R_DS(on) max": ["rds", "rdson", "on-resistance", "on resistance", "r_ds"],
    "V_DS": ["vds", "drain-source voltage", "breakdown"],
    "I_D continuous": ["current", "id ", "i_d"],
    "Q_g typical": ["gate charge", "qg", "q_g"],
    "operating temperature": ["temperature range", "operating temp", "temp range"],
    "power consumption typical": ["power consumption", "power"],
    "supply voltage": ["supply", "vcc", "vdd"],
}


class KB:
    def __init__(self, corpus: Corpus):
        self.c = corpus
        self.r = Retriever(corpus)
        self.parts = {normalize_pn(d["part"]): d["part"] for d in corpus.docs}

    def detect_part(self, q: str) -> str | None:
        for tok in re.findall(r"[A-Za-z0-9\-]{5,}", q):
            if normalize_pn(tok) in self.parts:
                return self.parts[normalize_pn(tok)]
        return None

    def detect_param(self, q: str) -> str | None:
        ql = q.lower()
        for param, aliases in PARAM_ALIASES.items():
            if any(a in ql for a in aliases):
                return param
        return None

    def ask(self, q: str) -> dict:
        part, param = self.detect_part(q), self.detect_param(q)
        if part and param:
            rows = [r for r in self.c.params if r["part"] == part and r["parameter"] == param and r["current"]]
            if rows:
                r = rows[0]
                cond = f" ({r['condition']})" if r.get("condition") else ""
                return {"answer": f"{part} {param}: {r['value']} {r['unit']}{cond}".strip(), "sources": [r["source"]], "route": "table"}
        doc_type = "pcn" if re.search(r"\b(pcn|eol|discontinu\w*|last time buy|replac\w*|end of life|requalif\w*|re-qualif\w*)\b", q, re.I) else None
        hits = self.r.search(q, k=3, part=part, doc_type=doc_type)
        if not hits:
            return {"answer": "Not found in the knowledge base. Please ask an FAE.", "sources": [], "route": "none"}
        return {"answer": " ".join(h["text"] for h in hits), "sources": [h["source"] for h in hits], "route": "retrieval"}
