import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as chromeLauncher from 'chrome-launcher';
import lighthouse from 'lighthouse';
import { chromium } from '@playwright/test';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const staticRoot = path.join(projectRoot, 'frontend/dist/nba-analytics/browser');
const reportPath = path.join(projectRoot, 'docs/quality/lighthouse-summary.json');
const mimeTypes = {
  '.css': 'text/css',
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.svg': 'image/svg+xml'
};

const listen = (server, port) =>
  new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });

const apiServer = http.createServer((request, response) => {
  response.setHeader('Access-Control-Allow-Origin', '*');
  response.setHeader('Content-Type', 'application/json');
  if (request.url === '/api/v1/coverage') {
    response.end(
      JSON.stringify({
        season_id: '2025-26',
        first_game_date: '2025-10-21',
        last_game_date: '2026-06-13',
        games: 1322,
        teams: 30,
        players: 591,
        player_game_rows: 34787,
        team_game_rows: 2644
      })
    );
    return;
  }
  response.statusCode = 404;
  response.end(JSON.stringify({ detail: 'Not found' }));
});

const staticServer = http.createServer(async (request, response) => {
  const requestPath = decodeURIComponent((request.url ?? '/').split('?')[0]);
  if (requestPath === '/config.js') {
    response.setHeader('Content-Type', 'text/javascript');
    response.end("window.__NBA_ANALYTICS_CONFIG__ = { apiBaseUrl: 'http://127.0.0.1:4411' };\n");
    return;
  }
  const relativePath = requestPath === '/' ? 'index.html' : requestPath.slice(1);
  const resolved = path.resolve(staticRoot, relativePath);
  if (!resolved.startsWith(`${staticRoot}${path.sep}`) && resolved !== staticRoot) {
    response.statusCode = 403;
    response.end('Forbidden');
    return;
  }
  try {
    const content = await fs.readFile(resolved);
    response.setHeader('Content-Type', mimeTypes[path.extname(resolved)] ?? 'application/octet-stream');
    response.end(content);
  } catch {
    response.statusCode = 404;
    response.end('Not found');
  }
});

let chrome;
try {
  await listen(apiServer, 4411);
  await listen(staticServer, 4400);
  chrome = await chromeLauncher.launch({
    chromePath: chromium.executablePath(),
    chromeFlags: ['--headless', '--no-sandbox']
  });
  const result = await lighthouse('http://127.0.0.1:4400', {
    port: chrome.port,
    logLevel: 'error',
    onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
    output: 'json'
  });
  if (!result) {
    throw new Error('Lighthouse returned no result');
  }
  const categories = Object.fromEntries(
    Object.entries(result.lhr.categories).map(([key, value]) => [key, value.score])
  );
  const summary = {
    generated_at: new Date().toISOString(),
    lighthouse_version: result.lhr.lighthouseVersion,
    categories,
    metrics: {
      first_contentful_paint_ms: result.lhr.audits['first-contentful-paint'].numericValue,
      largest_contentful_paint_ms: result.lhr.audits['largest-contentful-paint'].numericValue,
      total_blocking_time_ms: result.lhr.audits['total-blocking-time'].numericValue,
      cumulative_layout_shift: result.lhr.audits['cumulative-layout-shift'].numericValue
    }
  };
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, `${JSON.stringify(summary, null, 2)}\n`);
  console.log(JSON.stringify(summary, null, 2));

  const minimums = { performance: 0.8, accessibility: 0.95, 'best-practices': 0.9, seo: 0.9 };
  const failures = Object.entries(minimums).filter(
    ([category, minimum]) => (categories[category] ?? 0) < minimum
  );
  if (failures.length) {
    throw new Error(`Lighthouse thresholds failed: ${JSON.stringify(failures)}`);
  }
} finally {
  await chrome?.kill();
  await new Promise((resolve) => staticServer.close(resolve));
  await new Promise((resolve) => apiServer.close(resolve));
}
