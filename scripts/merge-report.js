#!/usr/bin/env node
/**
 * merge-report.js
 * ---------------
 * Produces MERGE_REPORT.md (or appends a new entry) after every Git merge.
 * Gathers: timestamp, branch, commit count, files changed, quality score.
 *
 * Usage:  node scripts/merge-report.js [--branch <name>] [--base <sha>]
 *
 * Cross-platform: pure Node.js (no bash / PowerShell calls except via child_process).
 */

'use strict';

const { execSync } = require('child_process');
const fs            = require('fs');
const path          = require('path');
const os            = require('os');

// ─── helpers ────────────────────────────────────────────────────────────────

function git(cmd, fallback = '') {
  try {
    return execSync(`git ${cmd}`, { encoding: 'utf8', stdio: ['pipe','pipe','pipe'] }).trim();
  } catch {
    return fallback;
  }
}

function node(cmd, cwd, fallback = '') {
  try {
    return execSync(cmd, { encoding: 'utf8', cwd: cwd || process.cwd(), stdio: ['pipe','pipe','pipe'] }).trim();
  } catch {
    return fallback;
  }
}

// ─── CLI args ────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const getArg = (flag) => {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : null;
};

const ROOT        = path.resolve(__dirname, '..');
const REPORT_FILE = path.join(ROOT, 'MERGE_REPORT.md');

// ─── git context ─────────────────────────────────────────────────────────────

const HEAD_SHA      = git('rev-parse HEAD');
const SHORT_SHA     = git('rev-parse --short HEAD');
const BRANCH        = getArg('--branch') || git('rev-parse --abbrev-ref HEAD', 'unknown');
const PREV_SHA      = getArg('--base')   || git('rev-parse HEAD~1', '');
const RANGE         = PREV_SHA ? `${PREV_SHA}..HEAD` : 'HEAD~5..HEAD';
const TIMESTAMP     = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

// ─── commit summary ───────────────────────────────────────────────────────────

const commitLog     = git(`log ${RANGE} --oneline`, '');
const commits       = commitLog ? commitLog.split('\n').filter(Boolean) : [];
const commitCount   = commits.length;

// Parse conventional commit types
const countType = (prefix) =>
  commits.filter(c => new RegExp(`\\b${prefix}(\\(.*?\\))?[!:]`).test(c)).length;
const featCount  = countType('feat');
const fixCount   = countType('fix');
const choreCount = countType('chore|ci|docs|style|refactor|test|perf');
const breakCount = commits.filter(c => /BREAKING CHANGE|!:/.test(c)).length;

// ─── files changed ────────────────────────────────────────────────────────────

const diffStat = git(`diff ${RANGE} --stat`, '');
const statLine = diffStat.split('\n').slice(-1)[0] || '';
// e.g. "12 files changed, 340 insertions(+), 45 deletions(-)"
const filesMatch = statLine.match(/(\d+) files? changed/);
const addMatch   = statLine.match(/(\d+) insertion/);
const delMatch   = statLine.match(/(\d+) deletion/);
const filesChanged  = filesMatch ? parseInt(filesMatch[1], 10) : 0;
const linesAdded    = addMatch   ? parseInt(addMatch[1], 10)   : 0;
const linesDeleted  = delMatch   ? parseInt(delMatch[1], 10)   : 0;

// Top changed files
const changedFiles = git(`diff ${RANGE} --name-only`, '').split('\n').filter(Boolean);
const topFiles = changedFiles.slice(0, 8).map(f => `  - \`${f}\``).join('\n') || '  _(none)_';

// ─── TODO/FIXME harvest (inline, fast) ────────────────────────────────────────

const TODO_RE = /\b(TODO|FIXME|HACK|XXX)\b.*$/gm;
let todoItems = [];
const searchExts = ['.ts','.tsx','.js','.jsx','.py','.md'];

function scanDir(dir, depth = 0) {
  if (depth > 6) return;
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const entry of entries) {
    if (['.git','node_modules','venv','.venv','__pycache__','.ruff_cache',
         'htmlcov','coverage','dist','build','.pytest_cache'].includes(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) { scanDir(full, depth + 1); continue; }
    if (!searchExts.includes(path.extname(entry.name))) continue;
    try {
      const src = fs.readFileSync(full, 'utf8');
      let m;
      while ((m = TODO_RE.exec(src)) !== null) {
        const line = src.slice(0, m.index).split('\n').length;
        todoItems.push({ file: path.relative(ROOT, full).replace(/\\/g,'/'), line, text: m[0].trim().slice(0, 120) });
      }
      TODO_RE.lastIndex = 0;
    } catch {}
  }
}
scanDir(ROOT);
const todoCount   = todoItems.length;
const todoSection = todoItems.slice(0, 15).map(t =>
  `  - [\`${t.file}:${t.line}\`] ${t.text}`).join('\n') || '  _(none found)_';

// ─── bundle size snapshot (frontend) ─────────────────────────────────────────

let bundleSizeKb = 0;
const distDir = path.join(ROOT, 'frontend', 'dist', 'assets');
if (fs.existsSync(distDir)) {
  const jsFiles = fs.readdirSync(distDir).filter(f => f.endsWith('.js'));
  bundleSizeKb = jsFiles.reduce((sum, f) => {
    try { return sum + fs.statSync(path.join(distDir, f)).size; } catch { return sum; }
  }, 0) / 1024;
}

// ─── type coverage (TypeScript — count any vs total) ─────────────────────────

let typeCoverageStr = 'N/A';
const tscOut = node('npx tsc --noEmit --strict 2>&1 || true', path.join(ROOT,'frontend'), '');
const errCount = (tscOut.match(/error TS/g) || []).length;
if (errCount === 0) typeCoverageStr = '✅ 0 TypeScript errors';
else typeCoverageStr = `⚠️ ${errCount} TypeScript error(s)`;

// ─── dependency vulnerability summary ────────────────────────────────────────

let vulnSummary = 'N/A (run `npm audit` manually)';
const auditOut = node('npm audit --json 2>/dev/null || true', ROOT, '{}');
try {
  const audit = JSON.parse(auditOut);
  const meta  = audit.metadata || {};
  const vuln  = meta.vulnerabilities || {};
  const total = Object.values(vuln).reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0);
  vulnSummary = total === 0
    ? '✅ No npm vulnerabilities'
    : `⚠️ ${total} npm vulnerability/ies (critical: ${vuln.critical||0}, high: ${vuln.high||0})`;
} catch {}

// ─── merge quality score ──────────────────────────────────────────────────────

let score = 100;
const scoreNotes = [];

if (breakCount > 0)       { score -= 20; scoreNotes.push(`-20 breaking changes (${breakCount})`); }
if (commitCount > 30)     { score -= 10; scoreNotes.push(`-10 large batch (${commitCount} commits)`); }
if (linesAdded > 2000)    { score -= 10; scoreNotes.push(`-10 large diff (+${linesAdded} lines)`); }
if (todoCount > 50)       { score -= 10; scoreNotes.push(`-10 high TODO debt (${todoCount} items)`); }
if (errCount > 0)         { score -= 15; scoreNotes.push(`-15 TypeScript errors (${errCount})`); }
if (featCount > 0)        { score +=  5; scoreNotes.push(` +5 features included (${featCount})`); }
if (fixCount > 0)         { score +=  3; scoreNotes.push(` +3 fixes included (${fixCount})`); }
score = Math.max(0, Math.min(100, score));

const scoreEmoji = score >= 85 ? '🟢' : score >= 60 ? '🟡' : '🔴';
const scoreLabel = score >= 85 ? 'Excellent' : score >= 60 ? 'Needs Attention' : 'Poor';

// ─── assemble report entry ────────────────────────────────────────────────────

const entry = `
## Merge Report — ${TIMESTAMP}

| Field | Value |
|---|---|
| **Branch** | \`${BRANCH}\` |
| **Commit (HEAD)** | \`${SHORT_SHA}\` |
| **Commits in merge** | ${commitCount} |
| **Files changed** | ${filesChanged} |
| **Lines added / deleted** | +${linesAdded} / -${linesDeleted} |
| **Breaking changes** | ${breakCount} |
| **Merge Quality Score** | ${scoreEmoji} **${score}/100** — ${scoreLabel} |

### Commit Breakdown
| Type | Count |
|---|---|
| feat | ${featCount} |
| fix | ${fixCount} |
| chore/ci/docs/refactor | ${choreCount} |
| breaking | ${breakCount} |

### Top Changed Files
${topFiles}

### Bundle Size Snapshot (frontend/dist/assets)
${bundleSizeKb > 0 ? `**${bundleSizeKb.toFixed(1)} KB** total JS (post-build snapshot)` : '_No production build found — run `npm run build` in `frontend/` to populate._'}

### TypeScript Health
${typeCoverageStr}

### Dependency Vulnerability Summary
${vulnSummary}

### TODO / FIXME Debt (top 15 of ${todoCount})
${todoSection}

### Quality Score Breakdown
${scoreNotes.length ? scoreNotes.map(n => `- ${n}`).join('\n') : '- No deductions — clean merge!'}

---
`;

// ─── write / append ───────────────────────────────────────────────────────────

let existing = '';
if (fs.existsSync(REPORT_FILE)) existing = fs.readFileSync(REPORT_FILE, 'utf8');

const header = existing.startsWith('# Merge Reports')
  ? ''
  : '# Merge Reports\n\nAutomatically generated after every merge to `main`.\n';

fs.writeFileSync(REPORT_FILE, header + entry + (existing.replace(/^# Merge Reports[\s\S]*?---\n/, '')).trimStart());

console.log(`[merge-report] Written to MERGE_REPORT.md`);
console.log(`[merge-report] Score: ${scoreEmoji} ${score}/100 — ${scoreLabel}`);
console.log(`[merge-report] Commits: ${commitCount}  Files: ${filesChanged}  TODOs: ${todoCount}`);

// also write a machine-readable snapshot for CI artefacts
const jsonOut = path.join(ROOT, 'merge-report.json');
fs.writeFileSync(jsonOut, JSON.stringify({
  timestamp: TIMESTAMP, branch: BRANCH, sha: HEAD_SHA,
  commitCount, filesChanged, linesAdded, linesDeleted,
  bundleSizeKb: +bundleSizeKb.toFixed(1), typescriptErrors: errCount,
  todoCount, score, scoreLabel,
}, null, 2));
console.log(`[merge-report] JSON artefact: merge-report.json`);
