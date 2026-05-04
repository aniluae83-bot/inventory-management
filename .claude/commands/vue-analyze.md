# Vue Component Analyzer

Analyze Vue component(s) for performance issues and code-reuse opportunities, following the `vue-analyze` skill guidelines.

**Target:** `$ARGUMENTS`
- If a `.vue` file path → analyze that file only
- If a directory path → glob `**/*.vue` within it
- If empty → analyze all files under `client/src/views/` and `client/src/components/`

---

## Step 1 — Collect files

Read every target `.vue` file in full.
Also read these for cross-cutting context (do NOT modify them):
- `client/src/api.js`
- `client/src/main.js`
- `client/src/composables/` (all files, if directory exists)
- `client/src/App.vue` (global styles reference)

---

## Step 2 — Per-component performance audit

For each component, check every item below and note `file:line` for each hit:

| Check | What to flag |
|---|---|
| **Method vs computed** | A `methods` function (or plain function in `<script setup>`) that is (a) called in `<template>` and (b) is a pure transformation — it should be `computed` |
| **v-for key** | `:key="index"` or missing `:key` on `v-for` |
| **v-if vs v-show** | `v-if` on something toggled on every user interaction (prefer `v-show`); `v-show` on something rendered once or rarely (prefer `v-if`) |
| **Inline heavy expressions** | Template expressions containing `.filter()`, `.map()`, `.sort()`, `.reduce()` that are not wrapped in a `computed` |
| **Deep watcher** | `watch(x, handler, { deep: true })` where a `computed` + shallow `watch` would suffice |
| **Sync-heavy onMounted** | Large sequential `await` chains in `onMounted` — flag if individual calls could be parallelised with `Promise.all` |
| **Oversized component** | Component > 300 lines — flag as a split candidate, suggest what to extract |
| **Sync route import** | Views imported as `import Foo from './views/Foo.vue'` in `main.js` — all views are candidates for `() => import(...)` lazy loading |

---

## Step 3 — Cross-component reuse audit

Scan across ALL target files together:

| Check | What to flag |
|---|---|
| **Duplicate logic** | The same utility function or data-transform appearing in ≥ 2 components → suggest a composable in `client/src/composables/` |
| **Duplicate loading/error boilerplate** | `loading = ref(false)` + `error = ref(null)` + try/catch scaffold repeated in ≥ 2 views → suggest a `useAsync(fn)` composable |
| **Duplicate template blocks** | Identical or near-identical HTML sections in ≥ 2 files → suggest a child component |
| **Duplicate scoped CSS** | Same CSS rule block appearing in ≥ 2 `<style scoped>` sections → suggest lifting to `App.vue` globals |
| **Duplicate API calls** | Same `api.*` call in ≥ 2 components without a shared composable → suggest centralising |
| **Props drilling** | A prop passed through 2+ component levels → suggest `provide`/`inject` or shared state |

---

## Step 4 — Output report

Print a structured Markdown report with these exact sections:

### Analysis Summary
Table: file name | line count | perf issues | reuse issues

### Performance Findings
Per file, bullet list of `[PERF-xxx] file:line — description`.
Skip files with zero findings.

### Reuse Findings
Per finding, list all affected files with line refs.
Group by type (duplicate logic / duplicate template / duplicate CSS / etc.).

### Prioritised Action List
Rank every finding **High / Medium / Low** and list in that order.
Criteria: High = affects render performance or is duplicated in 3+ files; Medium = 2 files or moderate perf impact; Low = style / minor.

### Top-3 Refactoring Examples
For the three highest-priority findings, show a concise before/after code snippet.
Keep snippets focused — show only the changed lines plus enough context to locate them.

---

## Constraints

- **Read only** — do not modify any file unless the user explicitly asks after seeing the report.
- Skip findings that match intentional patterns documented in `.claude/agents/vue-expert.md` (e.g. `useFilters` composable usage, loading/error state trio).
- If `$ARGUMENTS` points to a non-existent path, report the error and stop.
