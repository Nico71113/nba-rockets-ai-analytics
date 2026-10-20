import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const catalogPath = path.join(projectRoot, 'frontend/public/demo/catalog.json');
const forecastPath = path.join(
  projectRoot,
  'frontend/public/demo/three-point-forecast.json'
);
const catalog = JSON.parse(await fs.readFile(catalogPath, 'utf8'));
const forecast = JSON.parse(await fs.readFile(forecastPath, 'utf8'));
const failures = [];
const queryEntries = Object.entries(catalog.queries ?? {});

if (catalog.schema_version !== 1) failures.push('schema_version must be 1');
if (queryEntries.length !== 7) failures.push(`expected 7 showcase queries, found ${queryEntries.length}`);
if (catalog.coverage?.games !== 1322) failures.push('coverage.games must equal 1322');
if (catalog.coverage?.teams !== 30) failures.push('coverage.teams must equal 30');
if (!queryEntries.some(([, response]) => response.result?.method === 'sql')) {
  failures.push('catalog must contain at least one SQL answer');
}
if (!queryEntries.some(([, response]) => response.result?.method === 'refusal')) {
  failures.push('catalog must contain an honest refusal example');
}
if (forecast.cohort?.players !== 311) failures.push('forecast cohort must contain 311 players');
if (forecast.best_method !== 'shrinkage') failures.push('shrinkage must win the versioned backtest');
if (forecast.selected_prior_strength !== 200) {
  failures.push('forecast prior strength must equal the nested-validation result of 200');
}
if (forecast.methods?.length !== 3) failures.push('forecast must compare exactly three methods');
if (forecast.split?.training_end >= forecast.split?.testing_start) {
  failures.push('forecast training and testing periods must not overlap');
}
if (forecast.improvement_vs_historical_rmse_pct <= 0) {
  failures.push('forecast must report improvement against the historical-rate baseline');
}

for (const [question, response] of queryEntries) {
  if (response.question.toLocaleLowerCase('en-US') !== question) {
    failures.push(`query key is not normalized: ${question}`);
  }
  for (const evidence of response.result?.evidence ?? []) {
    for (const gameId of evidence.game_ids ?? []) {
      if (!catalog.games?.[gameId]) {
        failures.push(`missing evidence row ${gameId} for: ${question}`);
      }
    }
  }
}

if (failures.length) {
  throw new Error(`Demo catalog validation failed:\n- ${failures.join('\n- ')}`);
}

console.log(
  `Validated ${queryEntries.length} showcase queries, ${Object.keys(catalog.games).length} evidence rows, and the ${forecast.cohort.players}-player forecast backtest.`
);
