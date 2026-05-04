---
name: vue-analyze
description: Framework for auditing Vue 3 components in this project for performance issues and code-reuse opportunities. Use this skill when asked to review, audit, or suggest improvements for Vue components.
---

# Vue Component Analysis Framework

This skill defines the analysis methodology for Vue 3 components in the inventory management app. The project uses Vue 3 Composition API with `<script setup>`, Vite, scoped CSS, Axios, and the `useFilters` composable for shared filter state.

## Project Conventions (Do Not Flag These)

These patterns are intentional — do not report them as issues:

- `useFilters()` composable imported in views — this is the correct shared-state pattern
- The `loading / error / data` trio in every view (`loading = ref(false)`, `error = ref(null)`) — this is the approved pattern **unless** it is duplicated across 3+ views without a shared helper
- Scoped CSS per component — intentional; only flag identical blocks copied verbatim across files
- `v-if="loading"` / `v-else-if="error"` / `v-else` in templates — approved loading state pattern
- SVG chart components built inline — acceptable for this project's custom chart approach

---

## Performance Checks

### P1 — Methods vs Computed (High impact)

**Problem:** A plain function called in `<template>` re-executes on every render. A `computed` is cached until its reactive dependencies change.

**Flag when:** A function in `<script setup>` (or in `methods`) is:
1. Called or referenced in `<template>`, AND
2. Returns a derived value from reactive state without side effects

```vue
// BAD — runs on every render
function totalValue() {
  return items.value.reduce((s, i) => s + i.unit_cost * i.quantity, 0)
}
<span>{{ totalValue() }}</span>

// GOOD — cached
const totalValue = computed(() =>
  items.value.reduce((s, i) => s + i.unit_cost * i.quantity, 0)
)
<span>{{ totalValue }}</span>
```

### P2 — v-for Key Quality (High impact)

**Flag when:** `:key="index"` or no `:key` is used on `v-for`.

**Why:** Index keys cause Vue to reuse the wrong DOM nodes when items are inserted, removed, or reordered — leads to visual glitches and missed updates.

```vue
// BAD
<tr v-for="(item, i) in items" :key="i">

// GOOD — stable unique ID
<tr v-for="item in items" :key="item.sku">
<tr v-for="order in orders" :key="order.id">
```

### P3 — v-if vs v-show (Medium impact)

| Directive | Best for |
|---|---|
| `v-if` | Content rarely shown (modals, error states, empty states) |
| `v-show` | Content toggled repeatedly by user interaction (tabs, expand/collapse) |

**Flag:** `v-if` on an element toggled by a click handler that runs many times per session.
**Flag:** `v-show` on a modal or element that is only shown once (wasted initial render).

### P4 — Inline Template Expressions (High impact)

**Flag when:** `<template>` contains chained array operations not wrapped in `computed`.

```vue
// BAD — recalculates on every render
<tr v-for="item in items.filter(i => i.qty < i.reorder).sort(...)">

// GOOD
const lowStockItems = computed(() =>
  items.value.filter(i => i.quantity_on_hand < i.reorder_point)
    .sort((a, b) => a.quantity_on_hand - b.quantity_on_hand)
)
<tr v-for="item in lowStockItems" :key="item.sku">
```

### P5 — Deep Watchers (Medium impact)

**Flag:** `watch(source, handler, { deep: true })` — deep watches traverse the entire object tree on every mutation.

**Prefer:** A `computed` that extracts the specific nested value, then a shallow `watch` on that computed.

```js
// BAD
watch(filters, loadData, { deep: true })

// GOOD — only re-fires when these two fields change
const filterKey = computed(() => `${filters.warehouse.value}|${filters.category.value}`)
watch(filterKey, loadData)
```

### P6 — Sequential Awaits in onMounted (Medium impact)

**Flag:** Multiple `await api.*(...)` calls in sequence inside `onMounted` when they are independent.

```js
// BAD — second call waits for first to finish
onMounted(async () => {
  inventoryData.value = await api.getInventory()
  summaryData.value  = await api.getDashboardSummary()
})

// GOOD — run in parallel
onMounted(async () => {
  const [inv, sum] = await Promise.all([
    api.getInventory(),
    api.getDashboardSummary()
  ])
  inventoryData.value = inv.data
  summaryData.value   = sum.data
})
```

### P7 — Oversized Components (Medium impact)

**Flag:** Any `.vue` file > 300 lines.
**Suggest splitting when:**
- Template has a visually distinct section (e.g. a modal, a chart panel, a table) that is > ~60 lines
- The `<script setup>` block has multiple unrelated concerns

### P8 — Synchronous Route Imports (Low impact)

All views in `main.js` are currently imported statically. Each view that is not the default landing page (`/`) is a candidate for lazy loading:

```js
// Current — all bundles eagerly
import Inventory from './views/Inventory.vue'

// Lazy — split into separate chunk, loaded on demand
const Inventory = () => import('./views/Inventory.vue')
```

This reduces initial bundle size but adds a brief loading moment on first navigation. Recommend lazy loading all routes except `/` (Dashboard).

---

## Code-Reuse Checks

### R1 — Duplicate Async Data Pattern (High if ≥ 3 views)

Every view currently has this identical scaffold:

```js
const data    = ref([])
const loading = ref(false)
const error   = ref(null)

const loadData = async () => {
  loading.value = true
  error.value   = null
  try {
    const res = await api.getEndpoint(getCurrentFilters())
    data.value = res.data
  } catch (err) {
    error.value = 'Failed to load data'
  } finally {
    loading.value = false
  }
}
```

**Suggest** a `useAsync` composable when this pattern appears in ≥ 3 views:

```js
// client/src/composables/useAsync.js
export function useAsync(fetcher) {
  const data    = ref(null)
  const loading = ref(false)
  const error   = ref(null)

  const execute = async (...args) => {
    loading.value = true
    error.value   = null
    try {
      data.value = (await fetcher(...args)).data
    } catch (err) {
      error.value = err.message ?? 'Failed to load data'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}
```

### R2 — Duplicate Utility Functions (High if cross-file)

**Flag** the same formatting or calculation function copy-pasted across files:
- `formatCurrency(value)` — if defined in more than one component
- `formatDate(str)` — if defined in more than one component
- Status badge color helpers

**Suggest** extracting to `client/src/composables/useFormatters.js` or `client/src/utils.js`.

### R3 — Duplicate Template Blocks (Medium)

**Flag** HTML sections that are structurally identical across ≥ 2 files (same element tree, same class names, only the bound data differs). Candidates in this project:

- Table rows with the same column structure
- Card headers (`<div class="card-header"><h3>...</h3></div>`)
- Empty-state placeholders

**Suggest** a simple child component:

```vue
<!-- components/DataTable.vue -->
<script setup>
defineProps({ columns: Array, rows: Array, rowKey: String })
</script>
```

### R4 — Duplicate Scoped CSS (Low–Medium)

**Flag** when the same CSS rule block (≥ 3 rules) appears verbatim in multiple `<style scoped>` sections.

**Suggest** lifting to `App.vue` as a global utility class, since `App.vue` already defines the shared design tokens (`.card`, `.page-header`, `.loading`, `.error`, etc.).

### R5 — Repeated API Calls Without Caching (Medium)

**Flag** if the same `api.*` endpoint is called independently in multiple views on every mount, without any shared caching or store.

**Suggest** either:
- A dedicated composable that caches the last result: `useInventory()`, `useOrders()`
- Or a note that this is acceptable for this demo's simplicity if data freshness matters

### R6 — Props Drilling (Medium–High)

**Flag** a prop passed through ≥ 2 component levels.

**Suggest** `provide`/`inject` for deeply nested read-only data, or a shared `ref` exported from a composable for mutable state.

---

## Output Format

When reporting analysis results, always use this structure:

```
### Analysis Summary
| File | Lines | Perf Issues | Reuse Issues |
|------|-------|------------|--------------|
| ...  |  ...  |     ...    |     ...      |

### Performance Findings
**Orders.vue**
- [P1] Orders.vue:45 — `formatTotal()` called in template; should be computed
- [P2] Orders.vue:78 — `:key="index"` on order row v-for

### Reuse Findings
**[R1] Duplicate async scaffold** — found in Dashboard.vue, Inventory.vue, Orders.vue, Demand.vue
  All four views repeat the same loading/error/data pattern.

### Prioritised Action List
**High**
1. [R1] Extract useAsync composable — 4 views affected
2. [P1] Orders.vue:45 — convert formatTotal to computed
...

### Top-3 Refactoring Examples
...
```
