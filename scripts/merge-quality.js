#!/usr/bin/env node
/**
 * merge-quality.js
 * ----------------
 * Orchestrates all merge-quality checks in sequence and produces a final
 * summary.  Designed to be called from CI (after a push to main) and from
 * the local post-merge git hook.
 *
 * Checks performed:
 *   1. TODO/FIXME harvest         → TODO_REPORT.md
 *   2. Type coverage              → type-coverage-report.json
 *   3. Bundle size diff           → bundle-size-report.json  (if dist exists)
 *   4. Merge report generation    → MERGE_REPORT.md + merge-report.json
 *
 * Usage:  node scripts/merge-quality.js [--branch <name>] [--base <sha>]
 *         All flags are forwarded to merge-report.js.
 *
 * Cross-platform: pure Node.js.
 */

'use strict';

const { spawnSync } = require('child_process');
const path          = require('path');
const fs            = require('fs');

const ROOT    = path.resolve(__dirname, '..');
const SCRIPTS = __dirname;

function runScript(scriptName, extraArgs = []) {
  const label = `[merge-quality] ${scriptName}`;
  console.log(`\n${label} — starting...`);

  const result = spawnSync(
    process.execPath,            // node
    [path.join(SCRIPTS, scriptName), ...extraArgs],
    { cwd: ROOT, stdio: 'inherit', encoding: 'utf8' }
  );

  if (result.error) {
    console.error(`${label} — ERROR: ${result.error.message}`);
    return false;
  }
  if (result.status !== 0) {
    console.warn(`${label} — exited with code ${result.status}`);
    return false;
  }
  console.log(`${label} — ✅ done`);
  return true;
}

// ─── run all checks ───────────────────────────────────────────────────────────

const extraArgs = process.argv.slice(2);   // pass through --branch / --base

const results = {
  'harvest-todos.js'   : runScript('harvest-todos.js'),
  'type-coverage.js'   : runScript('type-coverage.js'),
  'bundle-size-check.js': runScript('bundle-size-check.js'),
  'merge-report.js'    : runScript('merge-report.js', extraArgs),
};

// ─── final summary ────────────────────────────────────────────────────────────

console.log('\n╔══════════════════════════════════════════╗');
console.log(  '║        Merge Quality Suite — Summary     ║');
console.log(  '╚══════════════════════════════════════════╝\n');

let passed = 0;
let failed = 0;
for (const [script, ok] of Object.entries(results)) {
  const icon = ok ? '✅' : '❌';
  console.log(`  ${icon}  ${script}`);
  ok ? passed++ : failed++;
}

// Read merge-report.json for final score if available
const jsonPath = path.join(ROOT, 'merge-report.json');
if (fs.existsSync(jsonPath)) {
  try {
    const r = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    const emoji = r.score >= 85 ? '🟢' : r.score >= 60 ? '🟡' : '🔴';
    console.log(`\n  ${emoji}  Merge Quality Score: ${r.score}/100 — ${r.scoreLabel}`);
    console.log(`      Branch : ${r.branch}`);
    console.log(`      Commits: ${r.commitCount}  |  Files: ${r.filesChanged}  |  TODOs: ${r.todoCount}`);
  } catch {}
}

console.log(`\n  ${passed} passed  /  ${failed} failed\n`);

if (failed > 0) {
  // Non-fatal in post-merge hook — just report
  process.exitCode = 1;
}
