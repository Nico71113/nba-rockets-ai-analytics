import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outputRoot = path.join(projectRoot, 'frontend/dist/nba-analytics/browser');
const config = `window.__NBA_ANALYTICS_CONFIG__ = {
  apiBaseUrl: '',
  demoMode: true
};
`;

await fs.writeFile(path.join(outputRoot, 'config.js'), config);
await fs.copyFile(path.join(outputRoot, 'index.html'), path.join(outputRoot, '404.html'));
await fs.writeFile(path.join(outputRoot, '.nojekyll'), '');
console.log(`Prepared GitHub Pages artifact at ${outputRoot}`);
