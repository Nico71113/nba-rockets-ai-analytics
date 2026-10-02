# Data Sources

This document records the provenance, license, retrieval method, and permitted
repository use for every external dataset before it enters the application.

## Selection requirements

Each source must provide enough information to verify:

1. provenance and ownership;
2. license or terms of use;
3. season and table coverage;
4. a reproducible download method;
5. whether raw or derived rows may be redistributed.

## Primary source

**NBA Dataset: Box Scores and Stats (1947 - Today)** by Eoin A Moore:

- Dataset: <https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores>
- Declared license: [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)
- Snapshot inspected: Kaggle version 515, published 2026-06-15
- Underlying source identified by the publisher: NBA.com

The source supplies game, team-game, and player-game CSV files. The public
repository does not mirror those raw files. `python -m ingestion.download`
retrieves them directly from Kaggle and records their version, byte sizes, and
SHA-256 hashes in a manifest.

The selected files are:

- `Games.csv`
- `TeamStatistics.csv`
- `PlayerStatistics.csv`
- `Players.csv`
- `TeamHistories.csv`
- `LeagueSchedule25_26.csv`

`PlayByPlay.parquet` is intentionally deferred because it is close to 1 GB.
It will be an optional later download limited to Rockets analysis after the
structured-data product is working.

## Secondary validation source

[BoxScore Lab](https://boxscorelab.com/downloads/) publishes 2025-26 team
game results, standings, and player season totals under CC BY 4.0. It is useful
for independent aggregate checks, but it does not contain player-by-game rows,
so it cannot power the main question set by itself.

## Distribution decision

Even though the selected Kaggle dataset declares CC0, all large source files
remain local and ignored by Git. The repository publishes transformation code,
checksums, schemas, tests, and attribution—not a replacement copy of the source
database.

## Implemented subset

- Season: 2025-26
- Structured scope: all 30 teams
- Product focus: Houston Rockets and Kevin Durant
- Play-by-play: not downloaded or used in the current version

The verified source snapshot contains 1,230 regular-season games across 30
teams, 82 Rockets regular-season games, and 78 Kevin Durant regular-season
player rows for Houston.
