# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System Demo with GitHub integration — Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack & Architecture

**Tech Stack:**
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded at startup via `server/mock_data.py`
- **No database** — all data in-memory during server runtime, resets on restart

**Data Flow:**
1. Vue component loads filters from URL or user input
2. Component calls `api.js` with filter parameters
3. HTTP GET request to FastAPI endpoint with query params
4. Backend filters in-memory data and validates with Pydantic models
5. Response returned as JSON
6. Component updates refs and computed properties
7. Template re-renders

**Filter System:**
- 4 global filters: Time Period, Warehouse, Category, Order Status
- Passed as query params: `?warehouse=A&category=Circuit&status=Delivered&month=2025-01`
- Each endpoint decides which filters apply (some ignore time period, inventory ignores month)
- Backend implements standard pattern: check for 'all' value, skip that filter

## Development Commands

### Starting Servers

**Backend (Python):**
```bash
cd server
uv venv && uv sync     # One-time setup: create env and install dependencies
uv run python main.py  # Runs on http://localhost:8001
```

**Frontend (Node):**
```bash
cd client
npm install            # One-time setup
npm run dev            # Runs on http://localhost:3000
```

Run each in a separate terminal. Backend startup takes ~2-3 seconds; Vite dev server is instant.

### Testing

**Backend tests:**
```bash
cd server
uv run pytest ../tests/backend -v              # All tests
uv run pytest ../tests/backend/test_orders.py # Single file
uv run pytest ../tests/backend -k test_name   # Specific test by name
```

**API Documentation:**
- Start backend, visit http://localhost:8001/docs
- Interactive Swagger UI to test endpoints without code

### Development Workflow

1. Make backend changes → Auto-reload handled by Uvicorn
2. Make frontend changes → Vite hot reloads (saves apply instantly)
3. Modify JSON data files → Must restart backend to reload
4. Modify Pydantic models → Restart backend

## Codebase Organization

**Key Files:**
- `server/main.py` - FastAPI app, route definitions, response models
- `server/mock_data.py` - Loads JSON files into memory at startup
- `client/src/api.js` - HTTP client, centralizes all API calls
- `client/src/App.vue` - Root component, global styles, layout
- `client/src/views/*.vue` - Page components (Dashboard, Inventory, Orders, etc.)

**Data Files:**
- `server/data/inventory.json` - SKU, warehouse, stock levels, categories
- `server/data/orders.json` - Order ID, status, dates, amounts
- `server/data/demand_forecasts.json` - Forecast data for demand view
- `server/data/backlog_items.json` - Backlog entries
- `server/data/spending.json` - Spending summary data
- `server/data/transactions.json` - Individual spending transactions

**Tests:**
- `tests/backend/test_*.py` - Backend endpoint tests
- Pattern: FastAPI TestClient, Pydantic model validation, filter verification

## API Endpoints

**Inventory:**
- `GET /api/inventory` - Filters: warehouse, category

**Orders:**
- `GET /api/orders` - Filters: warehouse, category, status, month

**Dashboard:**
- `GET /api/dashboard/summary` - All 4 filters
- Returns totals and key metrics

**Other:**
- `GET /api/demand` - Demand forecasts (no filters)
- `GET /api/backlog` - Backlog items (no filters)
- `GET /api/spending/summary` - Total spending (all filters)
- `GET /api/spending/monthly` - Monthly breakdown (all filters)
- `GET /api/spending/categories` - By category (all filters)
- `GET /api/spending/transactions` - Individual transactions (all filters)

## Detailed Documentation

**For backend development details**, see `server/CLAUDE.md`:
- API design principles and patterns
- Adding new endpoints
- Data model best practices
- Filtering implementation
- Error handling and testing
- Mock data management

**For frontend development details**, see `client/CLAUDE.md`:
- Vue 3 Composition API patterns
- Reactive state and computed properties
- Component communication and composables
- Styling and CSS best practices
- Performance optimization
- Testing components

## Key Patterns & Constraints

**Reactivity:**
- Refs hold raw data: `allOrders`, `inventoryItems`, `demand`
- Computed properties derive filtered/formatted data
- Use `.value` in script, no `.value` in template

**v-for Keys:**
- ❌ Never use array index as key
- ✅ Use unique ID from data: `sku`, `id`, `month`, etc.

**Date Handling:**
- Always validate before calling `.getMonth()` — data may have null/invalid dates
- Use ISO 8601 format (YYYY-MM-DD) in data and APIs

**Pydantic Models:**
- Update when JSON structure changes
- Models define both data shape and API response type
- Validation happens automatically

**Filtering:**
- Inventory: warehouse, category (no time dimension)
- Orders: warehouse, category, status, month (all 4 filters)
- Revenue goals: $800K/month single warehouse, $9.6M YTD across all

## Design System

- **Colors**: Slate/gray palette (#0f172a dark, #64748b mid, #e2e8f0 light)
- **Status**: green (Delivered), blue (Shipped), yellow (Processing), red (Backordered)
- **Charts**: Custom SVG with CSS Grid for layouts
- **UI Rule**: No emojis

## Code Documentation

- **Always document non-obvious logic changes with comments** — only add comments for the WHY (constraints, subtle invariants, workarounds), not the WHAT (well-named code already explains that)

## Common Pitfalls

1. Using index in v-for — causes DOM reuse bugs when data changes
2. Forgetting `.value` in script logic
3. Mutating props directly instead of emitting events
4. Not validating dates before parsing
5. Modifying global data instead of filtering copies
6. Missing Pydantic model updates when JSON changes
7. Inconsistent filter parameter names across endpoints

## Testing Checklist for Features

- [ ] Frontend loads data on mount
- [ ] Filters apply correctly (check query params in browser)
- [ ] Backend filters match selected filters
- [ ] Response data types match Pydantic models
- [ ] Edge cases handled: empty results, invalid input, null dates
- [ ] Numbers formatted correctly (currency, thousands separator)
- [ ] Charts render without errors
- [ ] Mobile layout works if applicable
