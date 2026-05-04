# CLAUDE.md — OrchestratorOne

Multi-agent M&A due diligence intake system. A coordinator agent routes intake documents to 6 specialist subagents, each with scoped tools and a focused system prompt.

---

## Agent Architecture

### Coordinator Agent (`orchestrator.py`)

- **Model**: `claude-sonnet-4-6`
- **System prompt**: `prompts/coordinator.txt`
- **Sees**: full intake request, deal metadata, prior routing history, subagent outputs
- **Responsibilities**: classify urgency, select workstreams, aggregate subagent analysis, produce final routing decision
- **Does NOT**: perform domain-specific analysis — delegates entirely to specialists
- **Tools available**: `lookup_deal_registry`, `route_to_workstream`, `escalate_to_human`

The coordinator runs a structured loop:
1. Classify intake → determine which workstreams apply
2. Spawn relevant specialist subagents in parallel
3. Collect `WorkstreamAnalysis` objects from each
4. Aggregate risk signals and routing recommendations
5. Call `route_to_workstream` or `escalate_to_human`

### Specialist Subagents

Each lives in `agents/<workstream>_agent.py` and implements the `SpecialistAgent` interface:

```python
class SpecialistAgent:
    workstream: str
    tools: list[Tool]        # scoped to workstream only
    system_prompt: str       # loaded from prompts/<workstream>.txt

    def analyze(self, intake: IntakeRequest) -> WorkstreamAnalysis: ...
```

Tool access is intentionally scoped — Tax agent cannot call `check_sanctions`, Compliance agent cannot call `route_to_workstream`. Routing authority belongs to the coordinator only.

| Agent | Tools Available |
|-------|----------------|
| Tax | `classify_document` |
| Legal | `classify_document` |
| Technology | `classify_document` |
| Financial | `classify_document` |
| HR | `classify_document` |
| Compliance | `classify_document`, `check_sanctions` |
| Coordinator | `lookup_deal_registry`, `route_to_workstream`, `escalate_to_human` |

---

## Tool Reference

### `classify_document`
Classifies a document by workstream relevance and sensitivity level.

```python
Input:  {document_text: str, document_type: str}
Output: {workstreams: list[str], sensitivity: "low"|"medium"|"high"|"critical", summary: str}
```

- Side effects: None (read-only)
- Safe to retry: Yes
- All specialists have access

---

### `check_sanctions`
Queries OFAC, EU, and UN consolidated sanctions lists for named entities.

```python
Input:  {entity_names: list[str], country_codes: list[str]}
Output: {hits: list[SanctionHit], clean: bool, checked_lists: list[str]}
```

- Side effects: External API call (logged to audit.log)
- Safe to retry: Yes (idempotent)
- **PreToolUse hook applies**: blocked if `deal_value_usd > 500_000_000` — requires human approval before the check executes
- Compliance agent only

---

### `lookup_deal_registry`
Checks internal deal registry for related or duplicate transactions.

```python
Input:  {target_name: str, acquirer_name: str}
Output: {related_deals: list[DealRecord], is_duplicate: bool, conflict_status: str | None}
```

- Side effects: Read-only registry query
- Safe to retry: Yes
- Coordinator only

---

### `route_to_workstream`
Creates a structured routing action and writes to the deal management platform.

```python
Input:  {
    workstream: str,
    priority: "low" | "medium" | "high" | "critical",
    assignee: str,
    context: RoutingContext    # Pydantic model
}
Output: {routing_id: str, timestamp: str, status: "queued" | "assigned"}
```

- Side effects: Writes to deal platform — **irreversible without manual cancellation**
- **PreToolUse hook applies**:
  - Blocked if sanctions hit found (`ctx.sanctions_hits_found == True`)
  - Blocked if `deal_value_usd > 500_000_000`
- Coordinator only

---

### `escalate_to_human`
Pauses the pipeline and sends a structured decision packet to compliance officer(s).

```python
Input:  {
    reason: str,
    context: EscalationContext,
    required_decision: str      # what the human must decide
}
Output: {escalation_id: str, notified: list[str], expected_response_hours: int}
```

- Side effects: Sends email and Slack notification
- This is a **designed workflow outcome**, not a failure mode
- All agents have access; subagents should call it confidently on ambiguous cases

---

## PreToolUse Hooks (`hooks/pre_tool_use.py`)

Hooks intercept tool calls BEFORE execution. They cannot be bypassed by the model — they run in the harness layer.

### Blocking Rules

```python
BLOCKING_RULES = [
    {
        "tool": "check_sanctions",
        "condition": lambda ctx: ctx.deal_value_usd > 500_000_000,
        "action": "block",
        "reason": "Deal exceeds $500M materiality threshold. Human approval required before sanctions screening."
    },
    {
        "tool": "route_to_workstream",
        "condition": lambda ctx: ctx.sanctions_hits_found,
        "action": "block",
        "reason": "Sanctions hit detected. Routing blocked pending compliance officer review."
    },
    {
        "tool": "route_to_workstream",
        "condition": lambda ctx: ctx.deal_value_usd > 500_000_000,
        "action": "block",
        "reason": "Deal exceeds materiality threshold. Senior partner sign-off required before routing."
    },
]
```

When a block fires, the hook automatically calls `escalate_to_human` with the blocking reason and full context — so the pipeline never silently stalls.

### Hook Response Shape

```python
{
    "blocked": True,
    "reason": str,
    "escalation_id": str,    # created automatically
    "action_required": str   # what the human must do to unblock
}
```

---

## Escalation Rules

### Specialist subagents MUST escalate when:
1. `check_sanctions` returns any hit (even a partial name match)
2. `classify_document` returns `sensitivity: "critical"`
3. Target jurisdiction includes a FATF grey-list or black-list country
4. Counterparty is identified as a state-owned enterprise in a restricted jurisdiction
5. Agent confidence in workstream assignment is below 70% (self-assessed in output)

### Coordinator MUST escalate when:
1. Three or more workstreams flag `"high"` or `"critical"` risk simultaneously
2. Duplicate deal found in registry with conflicting active status
3. Any specialist subagent returns an error or times out
4. Routing decision would assign to a workstream with no available assignee

---

## Audit Trail

Every tool call is appended to `audit.log` as a newline-delimited JSON record:

```json
{
  "ts": "2026-05-04T09:14:32Z",
  "agent_id": "compliance_agent",
  "tool": "check_sanctions",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "hook_fired": false,
  "hook_action": null,
  "escalation_id": null
}
```

Routing decisions include a `rationale` field (model-generated), `hook_result`, and `human_override` boolean.

---

## System Prompt Guidelines

Prompts live in `prompts/` — never hardcoded in Python.

**All specialist prompts must include:**
- Explicit workstream scope: "You are a [workstream] specialist. Do not perform analysis outside your domain."
- Instruction to name uncertainty: "If you lack information to reach a conclusion, state this explicitly and recommend escalation."
- Prohibition on fabricated references: "Do not cite specific statutes, regulations, or case law unless retrieved via a tool."

**Coordinator prompt must include:**
- Priority ordering for conflicting workstream signals
- Materiality threshold awareness ($500M)
- Explicit instruction that routing is irreversible and requires high confidence

---

## Code Conventions

- All agents implement `SpecialistAgent` interface (duck-typed, not ABC — keep it simple)
- Tool functions are pure where possible; side effects documented in docstring
- System prompts loaded from `prompts/` at runtime — changing a prompt doesn't require a code deploy
- No f-string SQL, shell commands, or subprocess calls — all external calls use typed API clients
- Type hints on all public functions
- Tests in `tests/` mirror `agents/` and `tools/` structure 1:1

---

## Adding a New Workstream

1. Add `agents/<workstream>_agent.py` following the `SpecialistAgent` interface
2. Add `prompts/<workstream>.txt` with a focused system prompt (see guidelines above)
3. Register in `orchestrator.py` → `WORKSTREAM_REGISTRY`
4. Add workstream-specific tools to `tools/` if needed; update `BLOCKING_RULES` if any are high-risk
5. Write `tests/test_<workstream>_agent.py` before shipping

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific suite
pytest tests/test_hooks.py -v
pytest tests/test_routing.py -v
pytest tests/test_tools.py -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

Tests use `unittest.mock` to stub external API calls (`check_sanctions`, deal registry). Hook tests use the real hook logic with synthetic context objects.
