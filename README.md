# NBA Rockets AI Analytics

An explainable, local-first NBA analytics assistant centered on the Houston
Rockets and Kevin Durant. The application will combine exact SQL aggregation
with retrieval-augmented generation so every answer can show its supporting
games, player rows, and calculation steps.

> Status: project foundation and data-source validation are in progress.

## Product scope

- Use 2025-26 structured data for all 30 NBA teams so Rockets results can be
  compared with opponents and league baselines.
- Make the default experience Rockets- and Kevin Durant-focused.
- Use SQL for totals, averages, rankings, filters, and multi-game reasoning.
- Use vector retrieval for game context and narrative explanations.
- Return evidence with each answer and give a specific missing-data reason
  instead of guessing.

## Planned stack

- Angular frontend
- FastAPI backend
- PostgreSQL with pgvector
- Ollama for local embeddings and answer generation
- Docker Compose for reproducible local setup

## Data policy

Raw third-party data will not be committed to this repository. Reproducible
download and transformation scripts, source attribution, license notes, and a
small permitted test fixture will be included instead. See
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Independence

This is a clean-room personal portfolio project. It does not contain code,
questions, data, or submission artifacts from any private technical
assessment. It is not affiliated with or endorsed by the NBA or the Houston
Rockets.
