# ADR-003 — Raw Messages API over claude-agent-sdk

**Status:** Accepted  
**Date:** 2026-05-04  
**Deciders:** Deal Technology Risk, Compliance Officer

---

## Context

The hackathon scenario specifies the Claude Agent SDK as the target platform.
The `claude-agent-sdk` package (PyPI: `claude-agent-sdk`, latest: 0.1.73) provides a
`query()` abstraction that handles the agent tool loop internally — tool calls are
dispatched and results injected without the caller seeing the intermediate steps.

OrchestratorOne uses `anthropic.Anthropic()` with `client.messages.create()` — the raw
messages API — instead. This was a deliberate decision made after evaluating the Agent SDK.

The decision turns on a single architectural constraint: **hooks must be in the critical path.**

---

## Decision

**Use the raw `anthropic` messages API with an explicit tool loop.**

The coordinator loop in `orchestrator.py` runs `client.messages.create()`, inspects
`stop_reason`, and on every `tool_use` response invokes `pre_tool_use_hook()` before
the tool executes. This gives us a mandatory, synchronous interception point on every
single tool call — no exceptions, no opt-outs.

The claude-agent-sdk `query()` call would remove this interception point from our control.

---

## The Core Constraint

`pre_tool_use_hook()` is not advisory. It is a hard block. When it returns `{"blocked": True}`,
the tool does not execute — period. Three rules are enforced this way:

1. `route_to_workstream` blocked if `deal_value_usd >= $500M` without a human override token
2. `route_to_workstream` blocked if `session_ctx["sanctions_hits_found"]` is True
3. `check_sanctions` blocked if `deal_value_usd >= $500M` without a human override token

For these blocks to be compliance-grade — not best-effort — they must be evaluated in the
critical path of every tool call. The evaluation reads `deal_value_usd` from the validated
`IntakeRequest`, never from model-generated fields. This is what makes the block
audit-defensible: a model cannot reason its way past it.

**The Agent SDK's internal tool loop makes this mandatory interception impossible.**

With `query()`, tool dispatch happens inside the SDK. The caller can register callbacks,
but callbacks are invoked after the SDK has already decided to execute the tool. A
"pre-tool-use callback" in the Agent SDK is an observer pattern — it fires before execution
but cannot cancel it deterministically without raising an exception that terminates the session.

Raising an exception on a blocked tool call is not equivalent to a clean block:
- It terminates the agent session rather than returning a structured escalation
- It bypasses the `session_ctx` update and audit log entry that the coordinator needs
- It makes the escalation path dependent on exception handling rather than tool results

For a system where "a sanctions hit that proceeds to routing" is the primary failure mode,
a callback-based hook is not a compliant implementation.

---

## Consequences

**Positive:**
- Hook enforcement is synchronous and mandatory — no execution path exists where a tool
  call bypasses `pre_tool_use_hook()`
- `stop_reason` dispatch is explicit: `tool_use`, `end_turn`, `max_tokens`, `stop_sequence`
  are each handled as distinct cases. The `max_tokens` → auto-escalate branch would be
  lost in the Agent SDK's unified response stream
- `session_ctx` is visible and auditable in the coordinator's own scope — no hidden SDK state
- The audit log records every tool call, hook decision, and escalation with content hashes;
  this is only possible when the caller controls the loop
- The explicit tool loop is what the coordinator's hard turn limit (`MAX_COORDINATOR_TURNS`)
  enforces — the Agent SDK does not expose a per-turn limit hook

**Negative:**
- More code to maintain: the tool loop, stop_reason dispatch, and message accumulation are
  ~80 lines that the Agent SDK would handle for us
- Session resumability is manual — if the coordinator needs to resume a paused session
  (e.g., after a human override is received), we manage message history explicitly rather
  than via SDK session IDs
- Future Agent SDK features (e.g., native multi-agent spawning, built-in tool permission
  scoping) would require an explicit migration to adopt

---

## Alternatives Rejected

**1. claude-agent-sdk `query()` with pre-tool-use callback**

The SDK supports registering a `pre_tool_use` callback. We evaluated this as a hook
replacement. Rejected because: (a) callbacks cannot cancel execution without raising, (b)
the exception path bypasses our structured escalation logic, (c) `session_ctx` would need
to be shared state rather than coordinator-owned scope — creating a coupling the compliance
design explicitly avoids.

**2. Hybrid: Agent SDK for non-compliance paths, raw API for compliance checks**

Rejected because the compliance check (whether to call `check_sanctions`, whether to block
`route_to_workstream`) is not separable from the routing path. Every routing decision is a
potential compliance decision. A hybrid would require routing all tool calls through the
raw API anyway — providing no benefit from the Agent SDK.

**3. Migrate to Agent SDK and enforce compliance post-hoc (audit + rollback)**

Rejected for the same reason as ADR-002 §Alternatives Rejected: by the time a routing
action is detected as non-compliant, it has already been written to the deal management
platform. Routing is irreversible without manual platform intervention. Post-hoc audit is
not a substitute for a pre-execution block on an irreversible action.

---

## Note on Future Migration

If the Agent SDK adds a first-class cancellable pre-tool-use hook — one that can return a
structured block result rather than raising — this decision should be revisited. The Agent
SDK's session management and native subagent spawning are genuinely useful, and we would
adopt them if the hook enforcement model were compatible. The raw API is not a philosophical
preference; it is the current implementation that satisfies the compliance constraint.
