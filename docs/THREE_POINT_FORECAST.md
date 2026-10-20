# Experiment: forecasting second-half three-point percentage

## Research question

Can first-half shooting data predict a player's second-half three-point
percentage more accurately than simply carrying the observed percentage
forward?

This experiment adds a different kind of evidence to ArcLine. The question
answering product tests whether a database result is correct; this backtest
tests whether a statistical estimate generalizes to games that had not yet
happened at fitting time.

## Leakage-aware design

The 1,230 regular-season games are ordered by date and split at the league
schedule midpoint:

| Segment | Dates | Games | Use |
| --- | --- | ---: | --- |
| First half | Oct. 21, 2025–Jan. 16, 2026 | 617 | Fit predictors |
| Second half | Jan. 17–Apr. 12, 2026 | 613 | Held-out evaluation |

The first half is split again on Dec. 2. Candidate shrinkage strengths are
evaluated from earlier-first-half data against later-first-half data. The
winning strength is locked before the held-out second half is scored. Changing
second-half makes changes the measured error but cannot change a fitted
prediction; a unit test enforces this invariant.

The final cohort contains 311 players with at least 25 three-point attempts in
each half. This produces a meaningful held-out rate but introduces an
availability/usage filter that is stated as a limitation rather than hidden.

## Compared methods

For player \(i\), let \(m_i\) be first-half makes, \(n_i\) be first-half
attempts, and \(\mu\) be the league's first-half three-point percentage.

1. **First-half rate:** \(m_i / n_i\).
2. **League mean:** predict \(\mu\) for every player.
3. **Empirical-Bayes shrinkage:**
   \((m_i + k\mu) / (n_i + k)\), where \(k\) is selected by nested temporal
   validation.

The candidate grid is 0, 1, 2, 5, 10, 20, 40, 60, 80, 100, 150, 200, 300,
500, and 1,000 prior attempts. Unweighted player-level RMSE chooses \(k=200\).
The grid and metric are declared before the held-out second half is evaluated.

## Results

Errors are expressed in three-point percentage points; lower is better.

| Method | MAE | RMSE | Attempt-weighted MAE | Attempt-weighted RMSE |
| --- | ---: | ---: | ---: | ---: |
| First-half rate | 5.67 | 7.42 | 4.93 | 6.43 |
| League mean | 4.84 | 5.99 | 4.27 | 5.17 |
| Empirical-Bayes shrinkage | **4.58** | **5.84** | **3.97** | **5.02** |

Shrinkage reduces RMSE by 21.3% relative to carrying the raw first-half rate
forward and by 2.5% relative to the league-mean baseline.

### Error by first-half volume

| First-half attempts | Players | Raw-rate RMSE | League RMSE | Shrinkage RMSE |
| --- | ---: | ---: | ---: | ---: |
| 25–74 | 85 | 9.95 | 6.82 | **6.77** |
| 75–149 | 112 | 7.19 | 6.61 | **6.36** |
| 150+ | 114 | 5.07 | 4.50 | **4.38** |

The raw percentage is least stable in the lowest-volume group. Shrinkage helps
in every volume tier, but the remaining errors show that makes and attempts do
not capture role, health, shot quality, or lineup changes.

## Houston reality check

Kevin Durant made 40.4% of 203 first-half attempts. The shrinkage model
predicted 38.1%; his held-out second-half rate was 42.1% over 247 attempts. The
raw first-half rate was closer for this player.

That exception is important. A method can improve cohort-level accuracy while
being worse for a particular established shooter. The product displays this
case beside the aggregate win so a reviewer can distinguish population
performance from player-specific judgment.

## Error analysis

The largest shrinkage misses include sharp rate changes in both directions.
The report shows the player, team, first-half rate, fitted prediction,
second-half rate, and absolute error. These rows are starting points for a
basketball investigation, not proof of a causal explanation. Useful follow-up
features would include shot location/quality, role and lineup stability,
injury/availability history, and multi-season shooting priors.

## Reproduce it

With the normalized snapshot present:

```bash
make forecast-report
```

This writes the deterministic public artifact at
`frontend/public/demo/three-point-forecast.json`. The running backend computes
the same report at:

```text
GET /api/v1/experiments/three-point-forecast
```

The implementation uses only the Python standard library and SQLAlchemy; it
does not require a notebook-only environment or a hidden model file.

## Limitations

- The 25-attempt requirement excludes many injured and low-usage players.
- Cohort eligibility checks second-half attempt volume. This does not enter any
  fitted prediction, but it limits the population to players with enough future
  opportunities to evaluate reliably.
- Makes and attempts omit shot quality, role, defensive attention, and lineup
  context.
- This is a single-season backtest. Repeating the same pre-registered protocol
  across multiple seasons is the next test of generalization.
