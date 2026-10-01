# Architecture

## Scope decision

The relational layer covers the full 2025-26 league, while the product's
default experience and eventual play-by-play retrieval focus on Houston and
Kevin Durant. This preserves league-wide comparisons without creating an
unnecessarily large all-league vector index.

```mermaid
flowchart TD
    A[CC0 Kaggle snapshot] --> B[Download + checksum manifest]
    B --> C[Streaming normalization]
    C --> D[(PostgreSQL)]
    C --> E[Data quality report]
    D --> F[Parameterized analytics functions]
    G[Rockets play-by-play] --> H[(pgvector)]
    F --> I[FastAPI query orchestrator]
    H --> I
    I --> J[Ollama answer synthesis]
    J --> K[Angular chat + evidence panel]
```

## Answer contract

Every answer will expose:

- `method`: `sql`, `hybrid`, or `refusal`;
- a concise answer;
- calculation steps for derived statistics;
- supporting game, team, player, or event identifiers;
- the data coverage used;
- a specific missing-data explanation when the answer is unsupported.

The language model will not calculate aggregates or execute arbitrary SQL.
Exact values come from parameterized, tested analytics functions; the model
only selects supported tools and explains their verified outputs.
