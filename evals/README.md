# Structured analytics evaluations

This directory tests the deterministic analytics layer independently of any
language model. The goal is to catch plausible-sounding but numerically wrong
answers before a response reaches the UI.

## What is evaluated

- exact totals, averages, records, scores, and supporting game IDs;
- inclusive date boundaries and separation of regular-season/playoff rows;
- DNP handling (an absence is not silently converted to a zero-point game);
- cross-table joins between player and team box scores;
- explicit refusals for unsupported fields, dates, game types, and empty result
  sets;
- relational integrity of the normalized 2025-26 snapshot, when it is present
  locally;
- provenance-manifest shape and checksum metadata.

`fixtures/mini_snapshot.json` is synthetic and small enough to verify by hand.
It is not copied from the private take-home project or from the downloaded NBA
dataset. `fixtures/structured_questions.json` contains the corresponding
questions and golden outputs. `fixtures/source_snapshot_expectations.json`
records coverage expectations for the fixed, checksummed public-data snapshot.

Run the entire project suite:

```bash
pytest
```

Run only these evaluations:

```bash
pytest evals/tests
```

With the local stack running, validate language coverage separately from exact
numeric correctness:

```bash
python -m evals.run_language_eval  # 100 routing/response-contract cases
python -m evals.run_golden_eval    # 20 exact answer/method/metric cases
```

The split is intentional: a question can reach the correct intent while still
returning the wrong number. The first suite catches routing regressions; the
second checks values and the evidence contract against independently computed
reference results.

The normalized-snapshot test skips when `data/processed/*.csv` is absent. Run
the documented data pipeline first to enable that integration check. All
synthetic golden cases still run without downloaded data or PostgreSQL.
