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
