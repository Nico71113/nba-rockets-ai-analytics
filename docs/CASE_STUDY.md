# Case study: trustworthy natural-language NBA analytics

## Problem

Traditional dashboards are precise but require users to learn the interface.
General-purpose chat systems accept natural language but can invent numbers or
hide how an answer was produced. ArcLine explores a narrower product question:
can a basketball question feel conversational while every numerical claim
remains reproducible from a fixed data snapshot?

The first product scope is the 2025–26 NBA season, with Houston and Kevin Durant
as the primary examples. The underlying pipeline covers all 30 teams so the
architecture is not hard-coded to one roster.

## Architecture decision

The system uses a hybrid router. A deterministic parser handles common,
unambiguous wording quickly. A local Ollama model may classify less predictable
wording into a small typed intent schema. The model never writes SQL and never
performs the final arithmetic. Entity resolution, filtering, aggregation, and
evidence selection happen in tested application code over PostgreSQL.

This boundary was chosen because the highest-risk failure is not an awkward
sentence; it is a plausible but false statistic. Every supported response
therefore includes an interpreted method, filters, coverage, and source game
IDs. Unsupported questions explain the missing field or scope instead of using
a generic refusal or guessing.

## What failed during development

Evaluation exposed several cases that looked harmless but changed meaning:

- partial-name matching confused similarly named players;
- threshold phrases such as "at least" could be routed as an average request;
- a correctly selected intent could still return an incorrect number;
- a dynamic accessibility attribute was rendered as an invalid literal value;
- a single generic refusal did not tell the user whether the missing input was
  live data, tracking data, video labels, or a date outside the snapshot.

Each failure produced a guard, test, or more explicit response contract. This
is also why language-routing evaluation and exact-answer evaluation are kept as
separate suites.

## Verification

- 1,322 games, 30 teams, 591 players, and 34,787 player-game rows pass
  cross-table and coverage checks.
- 100/100 language cases pass the expected intent and response-contract checks.
- 20/20 numerical golden cases match exact answers, methods, metrics, and
  coverage fields.
- 51 Python, 3 Angular, and 4 Playwright browser tests pass.
- Browser tests cover evidence expansion, CSV download, refusal behavior,
  mobile overflow, and serious accessibility violations.
- Latest Lighthouse scores: 95 Performance, 100 Accessibility, 96 Best Practices,
  and 100 SEO in the versioned local audit.
- CI also builds and smoke-tests the complete Docker stack.

## Limitations

This version is a historical snapshot, not a live-score product. It does not
contain player tracking, defensive assignments, play-by-play, or synchronized
video labels, so it refuses questions that would require those sources. Source
data is not redistributed; the repository records provenance and provides a
reproducible ingestion pipeline. Natural-language coverage is deliberately
bounded, and the response always shows the interpretation so a user can catch
a mismatch.

## Next experiment

The most valuable extension would be a separately evaluated tracking/video
layer for off-ball actions: cuts, screens, spacing changes, and the resulting
defensive reactions. That work needs a new data contract and human review
protocol rather than being inferred from box scores.
