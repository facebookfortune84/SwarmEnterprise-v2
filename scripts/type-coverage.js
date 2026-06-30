#!/usr/bin/env node
/**
 * type-coverage.js
 * ----------------
 * Reports TypeScript type coverage for the frontend by counting `any`-typed
 * expressions (via grep) vs total typed symbols (via tsc --listFiles),
 * then writes a summary to type-coverage-report.json.
 *
 * Usage:  node scripts/type-coverage.js
 *
 * Cross-platform: pure Node.js.
 */

'use strict';

const { execSync } = require('child_process');
const fs           = require('fs');
const path         = require('path');

const ROOT        = path.resolve(__dirname, '..');
const FRONTEND    = path.join(ROOT, 'frontend');
const OUTPUT_FILE = path.join(ROOT, 'type-coverage-report.json');

function run(cmd, cwd, fallback = '') {
  try {
    return execSync(cmd, { encoding: 'utf8', cwd, stdio: ['pipe','pipe','pipe'] }).trim();
  } catch (e) {
    return (e.stdout || '') + (e.stderr || '') || fallback;
  }
}

// ─── tsc diagnostics ──────────────────────────────────────────────────────────

const tscOut    = run('npx tsc --noEmit 2>&1 || true', FRONTEND, '');
const tsErrors  = (tscOut.match(/error TS\d+/g) || []).length;
const tsWarnings= (tscOut.match(/warning TS\d+/g) || []).length;

// ─── any-usage count (approximation) ─────────────────────────────────────────

function countAnyInDir(dir) {
  let count = 0;
  function walk(d) {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (['node_modules','dist','.git'].includes(e.name)) continue;
      const full = path.join(d, e.name);
      if (e.isDirectory()) { walk(full); continue; }
      if (!/\.(ts|tsx)$/.test(e.name)) continue;
      try {
        const src = fs.readFileSync(full, 'utf8');
        // count `: any` and `as any` usages (rough proxy for `any` density)
        count += (src.match(/:\s*any\b/g) || []).length;
        count += (src.match(/as\s+any\b/g) || []).length;
      } catch {}
    }
  }
  walk(dir);
  return count;
}

const anyCount = countAnyInDir(path.join(FRONTEND, 'src'));

// ─── total TS source lines ────────────────────────────────────────────────────

function countTsLines(dir) {
  let lines = 0;
  function walk(d) {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (['node_modules','dist'].includes(e.name)) continue;
      const full = path.join(d, e.name);
      if (e.isDirectory()) { walk(full); continue; }
      if (!/\.(ts|tsx)$/.test(e.name)) continue;
      try { lines += fs.readFileSync(full,'utf8').split('\n').length; } catch {}
    }
  }
  walk(dir);
  return lines;
}

const tsLines = countTsLines(path.join(FRONTEND, 'src'));

// ─── previous snapshot delta ──────────────────────────────────────────────────

let prevErrors = null;
let prevAny    = null;
if (fs.existsSync(OUTPUT_FILE)) {
  try {
    const prev = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'));
    prevErrors = prev.tsErrors;
    prevAny    = prev.anyCount;
  } catch {}
}

const report = {
  timestamp   : new Date().toISOString(),
  tsErrors,
  tsWarnings,
  anyCount,
  tsLines,
  anyDensityPer1000: tsLines > 0 ? +((anyCount / tsLines) * 1000).toFixed(2) : 0,
  deltaErrors : prevErrors !== null ? tsErrors - prevErrors : null,
  deltaAny    : prevAny    !== null ? anyCount - prevAny    : null,
};

fs.writeFileSync(OUTPUT_FILE, JSON.stringify(report, null, 2));

const errDelta = report.deltaErrors !== null ? ` (${report.deltaErrors >= 0 ? '+' : ''}${report.deltaErrors} vs last)` : '';
const anyDelta = report.deltaAny    !== null ? ` (${report.deltaAny >= 0    ? '+' : ''}${report.deltaAny} vs last)`    : '';

console.log(`[type-coverage] TS errors   : ${tsErrors}${errDelta}`);
console.log(`[type-coverage] \`any\` usages: ${anyCount}${anyDelta}  (${report.anyDensityPer1000}/1000 lines)`);
console.log(`[type-coverage] Source lines: ${tsLines}`);
console.log(`[type-coverage] Report written to type-coverage-report.json`);
