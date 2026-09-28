"""Ingestion: front-matter metadata, tables extracted as structured rows, prose chunked by paragraph.

Tables are NOT embedded as text: a spec question ('R_DS(on) of AS60R045?') is answered from the parameter
table with an exact citation; prose goes to the retriever. Superseded revisions are kept but excluded by default.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Chunk:
    text: str
    meta: dict
    source: str


@dataclass
class Corpus:
    chunks: list[Chunk] = field(default_factory=list)
    params: list[dict] = field(default_factory=list)      # structured table rows
    docs: list[dict] = field(default_factory=list)


def parse(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    return yaml.safe_load(fm), body.strip()


def ingest(folder: Path) -> Corpus:
    c = Corpus()
    for f in sorted(folder.glob("*.md")):
        meta, body = parse(f)
        meta["current"] = "superseded_by" not in meta
        meta["file"] = f.name
        c.docs.append(meta)
        table, prose = [], []
        for i, line in enumerate(body.splitlines(), 1):
            if line.startswith("|"):
                table.append((i, line))
            elif line.strip() and not line.startswith("#"):
                prose.append((i, line.strip()))
        rows = [[x.strip() for x in l.strip("|").split("|")] for _, l in table]
        if len(rows) > 2:
            header = rows[0]
            for (ln, _), r in zip(table[2:], rows[2:]):
                c.params.append({**dict(zip(header, r)), "part": meta["part"], "revision": meta.get("revision"),
                                 "current": meta["current"], "source": f"{f.name}:L{ln}"})
        title = next((l[2:] for l in body.splitlines() if l.startswith("# ")), f.stem)
        for ln, text in prose:
            c.chunks.append(Chunk(f"{title}. {text}", meta, f"{f.name}:L{ln}"))
    return c
