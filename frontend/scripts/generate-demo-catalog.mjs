import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const baseUrl = (process.env.ARCLINE_API_URL ?? 'http://localhost:8100').replace(/\/$/, '');
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outputPath = path.join(projectRoot, 'frontend/public/demo/catalog.json');
const questions = [
  "What was Houston's regular-season record in 2025-26?",
  'What did Kevin Durant average for Houston during the 2025-26 regular season?',
  "What was Houston's record when Kevin Durant scored at least 30 points?",
  "What was Houston's record when Kevin Durant made at least 4 three-pointers?",
  'How many total points did Houston score in January 2026?',
  "What was Kevin Durant's highest points total on the road?",
  'Which defender guarded Kevin Durant most often this season?'
];

const normalizeQuestion = (question) =>
  question.trim().toLocaleLowerCase('en-US').replace(/\s+/g, ' ');

const requestJson = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${url}`);
  }
  return response.json();
};

const coverage = await requestJson(`${baseUrl}/api/v1/coverage`);
const queryEntries = await Promise.all(
  questions.map(async (question) => {
    const response = await requestJson(`${baseUrl}/api/v1/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    return [normalizeQuestion(question), response];
  })
);
const queries = Object.fromEntries(queryEntries);
const gameIds = [
  ...new Set(
    queryEntries.flatMap(([, response]) =>
      response.result.evidence.flatMap((item) => item.game_ids)
    )
  )
];
const gameRows = gameIds.length
  ? await requestJson(
      `${baseUrl}/api/v1/evidence/games?game_ids=${encodeURIComponent(gameIds.join(','))}`
    )
  : [];
const games = Object.fromEntries(gameRows.map((row) => [row.game_id, row]));

const catalog = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  source: 'Captured from the tested ArcLine API against the fixed 2025-26 snapshot.',
  coverage,
  queries,
  games
};

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, `${JSON.stringify(catalog, null, 2)}\n`);
console.log(`Wrote ${queryEntries.length} queries and ${gameRows.length} evidence rows to ${outputPath}`);
