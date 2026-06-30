#!/usr/bin/env node
/**
 * bundle-size-check.js
 * ---------------------
 * Measures the JS/CSS bundle size of the Vite build output and compares it
 * against a stored baseline (bundle-size-baseline.json in repo root).
 *
 * On first run it writes the baseline.
 * On subsequent runs it reports the delta and warns if > 10 % regression.
 *
 * Usage:  node scripts/bundle-size-check.js [--write-baseline]
 *         (pass --write-baseline after a deliberate size increase to reset)
 *
 * Cross-platform: pure Node.js.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const ROOT          = path.resolve(__dirname, '..');
const DIST_ASSETS   = path.join(ROOT, 'frontend', 'dist', 'assets');
const BASELINE_FILE = path.join(ROOT, 'bundle-size-baseline.json');
const WARN_PERCENT  = 10; // % regression threshold

const args           = process.argv.slice(2);
const writeBaseline  = args.includes('--write-baseline');

// ─── measure ──────────────────────────────────────────────────────────────────

function measureDir(dir) {
  if (!fs.existsSync(dir)) return { totalBytes: 0, files: [] };
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files   = [];
  for (const e of entries) {
    if (!e.isFile()) continue;
    const full = path.join(dir, e.name);
    const size = fs.statSync(full).size;
    if (e.name.endsWith('.js') || e.name.endsWith('.css')) {
      files.push({ name: e.name, bytes: size });
    }
  }
  files.sort((a, b) => b.bytes - a.bytes);
  const totalBytes = files.reduce((s, f) => s + f.bytes, 0);
  return { totalBytes, files };
}

const current = measureDir(DIST_ASSETS);

if (current.totalBytes === 0) {
  console.warn('[bundle-size] No dist/assets found — run `npm run build` inside frontend/ first.');
  process.exit(0);
}

const kb = (b) => (b / 1024).toFixed(1) + ' KB';

// ─── baseline ─────────────────────────────────────────────────────────────────

if (writeBaseline || !fs.existsSync(BASELINE_FILE)) {
  fs.writeFileSync(BASELINE_FILE, JSON.stringify({
    timestamp : new Date().toISOString(),
    totalBytes: current.totalBytes,
    files     : current.files,
  }, null, 2));
  console.log(`[bundle-size] Baseline written: ${kb(current.totalBytes)}`);
  process.exit(0);
}

const baseline = JSON.parse(fs.readFileSync(BASELINE_FILE, 'utf8'));

// ─── diff ─────────────────────────────────────────────────────────────────────

const delta     = current.totalBytes - baseline.totalBytes;
const deltaPct  = baseline.totalBytes > 0 ? (delta / baseline.totalBytes) * 100 : 0;
const deltaStr  = (delta >= 0 ? '+' : '') + kb(delta);
const deltaSign = delta >= 0 ? '▲' : '▼';

console.log(`[bundle-size] Baseline : ${kb(baseline.totalBytes)}`);
console.log(`[bundle-size] Current  : ${kb(current.totalBytes)}`);
console.log(`[bundle-size] Delta    : ${deltaSign} ${deltaStr} (${deltaPct.toFixed(1)}%)`);

if (current.files.length > 0) {
  console.log('[bundle-size] Top chunks:');
  current.files.slice(0, 5).forEach(f => console.log(`               ${f.name} — ${kb(f.bytes)}`));
}

// ─── write JSON artefact for merge-report ─────────────────────────────────────

const artefactPath = path.join(ROOT, 'bundle-size-report.json');
fs.writeFileSync(artefactPath, JSON.stringify({
  timestamp   : new Date().toISOString(),
  baselineKb  : +(baseline.totalBytes / 1024).toFixed(1),
  currentKb   : +(current.totalBytes  / 1024).toFixed(1),
  deltaKb     : +(delta / 1024).toFixed(1),
  deltaPct    : +deltaPct.toFixed(1),
  topChunks   : current.files.slice(0, 5).map(f => ({ name: f.name, kb: +(f.bytes/1024).toFixed(1) })),
}, null, 2));

// ─── gate ─────────────────────────────────────────────────────────────────────

if (deltaPct > WARN_PERCENT) {
  console.error(`[bundle-size] ⚠️  Bundle grew by ${deltaPct.toFixed(1)}% — exceeds ${WARN_PERCENT}% threshold.`);
  console.error('[bundle-size]    Review new dependencies. Run with --write-baseline to accept.');
  process.exitCode = 1;
} else {
  console.log(`[bundle-size] ✅ Bundle size within threshold (${deltaPct.toFixed(1)}% change).`);
}
