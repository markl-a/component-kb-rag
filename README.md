# component-kb-rag

**Knowledge base for electronic-component datasheets and PCN/EOL notices: spec tables answered from structured rows, prose answered by hybrid retrieval, superseded revisions excluded, out-of-scope questions refused — with an evaluation set that gates CI.**

Portfolio demo (Sept 2026). No external services; the documents are **fictional parts with illustrative values**. 6 tests + a 12-question eval.

```
docs/*.md (front-matter: part, doc_type, revision, effective, supersedes)
   │ ingest
   ├── tables  ──► structured rows (part × parameter × value × condition × source line)
   └── prose   ──► chunks with metadata
ask(q) ─► detect part + parameter ─► table hit? answer with exact cell citation
                                  └► else: metadata filter (part, pcn?) ─► BM25 + char-trigram, RRF fusion ─► threshold ─► answer | "Not found"
```

## Design choices that matter in this domain

| Problem | What this does |
|---|---|
| **Spec values live in tables**; chunking tables as text garbles them | Tables are parsed into rows; "Rds(on) of AS60R045" is answered from the row with its `file:line` citation |
| **Datasheets have revisions** | Superseded revisions are ingested but excluded by default — the test checks the rev-2 gate charge (68 nC) wins over rev-1 (75 nC) |
| **Part numbers are written many ways** (`as60r045`, `AS-60R045`) | Normalised matching + character-trigram retrieval |
| **Keyword vs meaning** | BM25 and trigram rankings fused with Reciprocal Rank Fusion; small stemmer and domain synonyms (EOL, LTB, replacement) |
| **Filter before scoring** | PCN/EOL questions are restricted to PCN documents; part filter applied first |
| **Don't invent** | The part number is excluded from relevance scoring once it is used as a filter, so "price of AS60R045" finds nothing relevant and returns *Not found* instead of a datasheet paragraph |

## Evaluation (and what it caught)

`python -m eval.run_eval` — citation hit (right document cited) and answer containment over 12 questions, including one that must be refused. CI fails below 0.9.

First run: **citation 0.917 / answer 0.833**. It caught two real bugs: "What *replaces* AS60R070?" missed the chunk that says "replace*ment*", and the price question returned a datasheet paragraph instead of refusing. Fixes: consistent stemming, stem-keyed synonyms, and not letting the part number count as relevance evidence. Now **1.0 / 1.0**.
Caveat: 12 questions, and they were used during development — this is a regression gate, not a held-out benchmark.

## Run

```bash
pip install -r requirements.txt
pytest -q
python -m eval.run_eval
python -c "from kb.answer import KB; from kb.ingest import ingest; from pathlib import Path; print(KB(ingest(Path('docs'))).ask('last time buy for AS60R070?'))"
```

## Swap-ins for production

Dense embeddings (e.g. multilingual-e5 / BGE-M3) as a third ranker in the RRF · pgvector or Azure AI Search as the index · PDF/table extraction (layout-aware) instead of markdown tables · an LLM to phrase the final answer from the cited rows only.
Pairs with **erp-copilot-agent** (quotes and PCN impact from ERP data).
