import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const coverage = {
  season_id: '2025-26',
  first_game_date: '2025-10-21',
  last_game_date: '2026-06-13',
  games: 1322,
  teams: 30,
  players: 591,
  player_game_rows: 34787,
  team_game_rows: 2644
};

const metricResponse = {
  question: 'How many total points did Houston score in January 2026?',
  intent: 'metric_summary',
  routing_source: 'deterministic',
  elapsed_ms: 24,
  interpretation: {
    intent: 'metric_summary',
    team_name: 'Houston Rockets',
    stat: 'points',
    aggregation: 'sum',
    start_date: '2026-01-01',
    end_date: '2026-01-31'
  },
  result: {
    method: 'sql',
    answer:
      'Houston Rockets recorded 1834 total points across 17 qualifying games from 2026-01-01 through 2026-01-31.',
    metrics: { games: 17, value: 1834, stat: 'points', aggregation: 'sum' },
    calculation: [
      'Filter team-game rows by date and game type.',
      'Apply the registered sum operation to the points field.'
    ],
    evidence: [
      {
        source_table: 'team_game_stats + games',
        snapshot_id: 'public-snapshot@515',
        game_ids: ['22500471'],
        filters: { team_id: 1610612745, start_date: '2026-01-01', end_date: '2026-01-31' }
      }
    ],
    coverage_note: null
  }
};

const refusalResponse = {
  question: 'Which defender guarded Kevin Durant most often this season?',
  intent: 'unsupported',
  routing_source: 'coverage_guard',
  elapsed_ms: 1,
  interpretation: { intent: 'unsupported' },
  result: {
    method: 'refusal',
    answer:
      'The loaded snapshot has no player-tracking or defensive-assignment data needed to identify who guarded a player.',
    metrics: {},
    calculation: [],
    evidence: [],
    coverage_note:
      'The loaded snapshot has no player-tracking or defensive-assignment data needed to identify who guarded a player.'
  }
};

const forecastResponse = {
  season_id: '2025-26',
  question: "Can first-half data predict a player's second-half three-point percentage?",
  split: {
    training_start: '2025-10-21',
    training_end: '2026-01-16',
    testing_start: '2026-01-17',
    testing_end: '2026-04-12',
    validation_training_end: '2025-12-02',
    validation_start: '2025-12-03',
    training_games: 617,
    testing_games: 613
  },
  cohort: {
    players: 311,
    minimum_attempts_per_half: 25,
    validation_players: 316,
    validation_minimum_attempts: 10
  },
  league_first_half_percentage: 0.358689,
  selected_prior_strength: 200,
  validation_rmse: 0.078098,
  selection_metric: 'unweighted player-level RMSE',
  methods: [
    {
      key: 'historical_rate',
      label: 'First-half rate',
      description: 'Use the observed rate without adjustment.',
      metrics: { mae: 0.05669, rmse: 0.074206, attempt_weighted_mae: 0.049, attempt_weighted_rmse: 0.064 }
    },
    {
      key: 'league_mean',
      label: 'League mean',
      description: 'Give every player the league rate.',
      metrics: { mae: 0.048428, rmse: 0.059911, attempt_weighted_mae: 0.043, attempt_weighted_rmse: 0.052 }
    },
    {
      key: 'shrinkage',
      label: 'Empirical-Bayes shrinkage',
      description: 'Partially pool the player rate toward the league.',
      metrics: { mae: 0.045838, rmse: 0.058432, attempt_weighted_mae: 0.04, attempt_weighted_rmse: 0.05 }
    }
  ],
  best_method: 'shrinkage',
  improvement_vs_historical_rmse_pct: 21.3,
  improvement_vs_league_rmse_pct: 2.5,
  volume_buckets: [
    {
      label: '25–74 attempts',
      minimum_attempts: 25,
      maximum_attempts: 74,
      players: 85,
      methods: {
        historical_rate: { mae: 0.076, rmse: 0.099459, attempt_weighted_mae: 0.07, attempt_weighted_rmse: 0.09 },
        league_mean: { mae: 0.053, rmse: 0.068233, attempt_weighted_mae: 0.05, attempt_weighted_rmse: 0.06 },
        shrinkage: { mae: 0.051, rmse: 0.067732, attempt_weighted_mae: 0.04, attempt_weighted_rmse: 0.06 }
      }
    }
  ],
  largest_misses: [
    {
      player_id: 1,
      player_name: 'Example Player',
      primary_team: 'Example Team',
      first_half_made: 16,
      first_half_attempts: 39,
      first_half_percentage: 0.410256,
      predicted_percentage: 0.367104,
      second_half_made: 7,
      second_half_attempts: 39,
      actual_percentage: 0.179487,
      absolute_error: 0.187617
    }
  ],
  featured_player: {
    player_id: 201142,
    player_name: 'Kevin Durant',
    primary_team: 'Houston Rockets',
    first_half_percentage: 0.403941,
    league_mean_prediction: 0.358689,
    shrinkage_prediction: 0.381483,
    second_half_percentage: 0.421053,
    first_half_attempts: 203,
    second_half_attempts: 247
  },
  findings: [],
  limitations: ['Single-season backtest.']
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/coverage', (route) => route.fulfill({ json: coverage }));
  await page.route('**/api/v1/query', async (route) => {
    const question = String(route.request().postDataJSON()?.question ?? '');
    await route.fulfill({
      json: question.includes('defender') ? refusalResponse : metricResponse
    });
  });
  await page.route('**/api/v1/evidence/games**', (route) =>
    route.fulfill({
      json: [
        {
          game_id: '22500471',
          game_date: '2026-01-01',
          game_type: 'Regular Season',
          away_team: 'Houston Rockets',
          home_team: 'Brooklyn Nets',
          away_score: 120,
          home_score: 96,
          winner: 'Houston Rockets'
        }
      ]
    })
  );
  await page.route('**/api/v1/experiments/three-point-forecast', (route) =>
    route.fulfill({ json: forecastResponse })
  );
});

test('answers a question, exposes evidence, and exports CSV', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('1,322')).toBeVisible();

  await page.locator('.more-suggestions summary').click();
  await page.getByRole('button', { name: 'January scoring' }).click();
  await expect(page.getByRole('heading', { name: /recorded 1834 total points/ })).toBeVisible();
  await expect(page.getByText('deterministic · 24 ms · metric summary')).toBeVisible();

  await page.locator('.evidence-block summary').click();
  await page.getByRole('button', { name: 'Load game details' }).click();
  await expect(page.getByRole('cell', { name: 'Houston Rockets at Brooklyn Nets' })).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('arcline-evidence.csv');
});

test('explains unsupported questions instead of guessing', async ({ page }) => {
  await page.goto('/');
  await page.locator('.more-suggestions summary').click();
  await page.getByRole('button', { name: 'Test a limitation' }).click();

  await expect(page.getByText('Honest refusal')).toBeVisible();
  await expect(page.getByRole('heading', { name: /no player-tracking/ })).toBeVisible();
  await expect(page.getByText('coverage guard · 1 ms · unsupported')).toBeVisible();
});

test('shows a leakage-aware forecast comparison and player-level error analysis', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'View forecast lab' }).click();

  await expect(
    page.getByRole('heading', { name: 'Can first-half shooting predict the second half?' })
  ).toBeVisible();
  await expect(page.getByText('21.3% lower RMSE')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Empirical-Bayes shrinkage' })).toBeVisible();
  await expect(page.getByText('Future leakage')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'The cohort winner is not universal' })).toBeVisible();
});

test('has no serious accessibility violations in the answered state', async ({ page }) => {
  await page.goto('/');
  await page.locator('.more-suggestions summary').click();
  await page.getByRole('button', { name: 'January scoring' }).click();
  await expect(page.getByRole('heading', { name: /recorded 1834 total points/ })).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((violation) =>
    ['serious', 'critical'].includes(violation.impact ?? '')
  );
  expect(serious).toEqual([]);
});

test('remains usable without horizontal overflow on a phone viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Ask a basketball question/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run query' })).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
});
