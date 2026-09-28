"""Hybrid retrieval without external services: BM25 (words) + character trigram overlap (robust to part-number
spelling), fused with Reciprocal Rank Fusion. Metadata filter runs BEFORE scoring."""
from __future__ import annotations

import math
import re
from collections import Counter

from .ingest import Chunk, Corpus

WORD = re.compile(r"[a-z0-9]+")
# keyed by stem; values are expanded then stemmed
SYNONYMS = {"eol": ["discontinued", "end", "life"], "ltb": ["last", "time", "buy"], "replac": ["recommended"],
            "rdson": ["r_ds", "resistance"], "temp": ["temperature"], "application": ["target", "use"]}


STOP = {"a", "an", "the", "is", "are", "of", "for", "what", "which", "do", "does", "i", "to", "in", "on", "it", "its",
        "and", "or", "how", "when", "after", "need", "there", "this", "that", "be", "with", "by", "any"}


def stem(w: str) -> str:
    """Tiny suffix stripper: replaces/replacement/replace -> replac. Enough for a small technical corpus."""
    for suf in ("ments", "ment", "ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    return w[:-1] if len(w) > 4 and w.endswith("e") else w


def words(t: str, drop: set[str] = frozenset()) -> list[str]:
    toks = [stem(w) for w in WORD.findall(t.lower()) if w not in STOP and w not in drop]
    return toks + [stem(s) for w in toks for s in SYNONYMS.get(w, [])]


def trigrams(t: str) -> Counter:
    s = re.sub(r"[^a-z0-9]", "", t.lower())
    return Counter(s[i:i + 3] for i in range(len(s) - 2))


def normalize_pn(t: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", t.upper())


class Retriever:
    def __init__(self, corpus: Corpus):
        self.c = corpus
        n = len(corpus.chunks)
        self.toks = [words(ch.text) for ch in corpus.chunks]
        self.tri = [trigrams(ch.text) for ch in corpus.chunks]
        df = Counter(t for ts in self.toks for t in set(ts))
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.avg = sum(map(len, self.toks)) / max(n, 1)

    def _bm25(self, q, i, k1=1.4, b=0.75):
        tf, dl = Counter(self.toks[i]), len(self.toks[i])
        return sum(self.idf.get(t, 0) * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / self.avg)) for t in q)

    def _tri(self, qt, i):
        inter = sum((qt & self.tri[i]).values())
        return inter / (sum(qt.values()) or 1)

    def search(self, query: str, k: int = 3, part: str | None = None, doc_type: str | None = None,
               include_superseded: bool = False, min_bm25: float = 1.0) -> list[dict]:
        cand = [i for i, ch in enumerate(self.c.chunks)
                if (include_superseded or ch.meta["current"])
                and (not part or normalize_pn(ch.meta["part"]) == normalize_pn(part))
                and (not doc_type or ch.meta["doc_type"] == doc_type)]
        # the part filter already enforces the part number, so it must not also count as relevance evidence:
        # "price of AS60R045" should score 0 on a datasheet that never mentions price.
        drop = {w for w in WORD.findall(query.lower()) if part and normalize_pn(w) == normalize_pn(part)}
        drop |= {w for w in WORD.findall((part or "").lower())}
        q, qt = words(query, drop), trigrams(" ".join(words(query, drop)))
        bm = {i: self._bm25(q, i) for i in cand}
        tr = {i: self._tri(qt, i) for i in cand}
        rank_b = {i: r for r, i in enumerate(sorted(cand, key=lambda i: -bm[i]))}
        rank_t = {i: r for r, i in enumerate(sorted(cand, key=lambda i: -tr[i]))}
        fused = sorted(cand, key=lambda i: -(1 / (60 + rank_b[i]) + 1 / (60 + rank_t[i])))
        hits = [i for i in fused if bm[i] >= min_bm25][:k]          # threshold: better to return nothing than noise
        return [{"text": self.c.chunks[i].text, "source": self.c.chunks[i].source, "part": self.c.chunks[i].meta["part"],
                 "doc_type": self.c.chunks[i].meta["doc_type"], "bm25": round(bm[i], 2)} for i in hits]
