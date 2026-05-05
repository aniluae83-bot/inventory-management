# ADR-002: PreToolUse Hooks as Compliance Guardrails over Prompt-Based Instructions

**Status:** Accepted  
**Date:** 2026-05-04  
**Deciders:** Anil Sharma (OrchestratorOne)

---

## Context

OrchestratorOne must enforce three compliance-critical blocking rules:

1. `check_sanctions` must not execute on deals above the $500M materiality threshold without prior human approval.
2. `route_to_workstream` must not execute if a sanctions hit has been detected in the current session.
3. `route_to_workstream` must not execute on deals above $500M without a logged senior partner approval record.

Violations of any of these rules produce outcomes with real legal and regulatory consequence: an autonomous material commitment that bypasses the firm's approval matrix, or a routing decision that proceeds past a flagged sanctions match. The question is not whether to enforce these rules — it is where enforcement lives.

The naive answer is: enforce in the system prompt. Instruct the coordinator agent not to call these tools under these conditions. This is necessary but not sufficient.

---

## The Core Distinction

**Prompt-based guardrail:** "Do not route a deal above $500M without senior approval."

The model reads this instruction and, under normal operating conditions, complies. Under adversarial conditions — elevated urgency in the intake document, prompt injection in document content, an unusual tool call sequence that distributes the decision across turns — compliance is probabilistic. There is no enforcement mechanism; there is instruction-following, which is a model behavior, not a code property.

**Hook-based guardrail:** A Python function evaluates `ctx.deal_value_usd > 500_000_000` against deal metadata sourced from the validated intake record — not from agent-generated fields. If true, the tool call is blocked. The model has no input to this decision.

The distinction matters for compliance frameworks. Regulated decisions require deterministic, auditable, code-enforced gates. Prompts are appropriate for *behavioral guidance*. They are not appropriate for *compliance enforcement*.

---

## Decision

Enforce all three blocking rules via **Claude Code PreToolUse hooks** (`hooks/pre_tool_use.py`), not via instructions in agent system prompts.

Hooks intercept tool calls before execution in the harness layer. They are evaluated in Python against deal metadata retrieved from the validated intake record — independently of any agent-generated fields. They cannot be bypassed by:

- Model output (including an agent that "reasons" its way around the restriction)
- Prompt injection embedded in intake documents
- An unusual sequence of tool calls that distributes the decision across turns
- A future model update that changes instruction-following behavior

Prompt-based instructions remain in place as a redundant secondary layer ("Do not call `route_to_workstream` if a sanctions hit has been returned") but are not relied upon for compliance enforcement. They provide defense-in-depth; the hook provides the hard floor.

---

## Implementation

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

When a block fires:

1. The tool call is rejected before execution.
2. `escalate_to_human` is called automatically with the blocking reason and full context — the pipeline never silently stalls.
3. The block event is appended to `audit.log` with `hook_fired: true`, the hook reason, and an `escalation_id`.
4. A structured block response is returned to the coordinator so it can acknowledge the block in its next turn.

Context (`ctx`) is constructed from the validated intake record at session initialization — it reads `deal_value_usd` from the typed `IntakeRequest` object, not from the coordinator's output. An agent cannot influence hook evaluation by generating a field value in its response.

---

## Consequences

### Positive

- A model reasoning error, a prompt injection in the intake document, or a future API update that changes instruction-following behavior cannot bypass the hook. The enforcement mechanism is code.
- Hooks fire and create an `escalation_id` automatically — the compliance officer receives notification regardless of the model's response to the block.
- Hook logic is inspectable without reading model behavior. A compliance officer or auditor can read `hooks/pre_tool_use.py` — under 50 lines of Python — and understand exactly what the system blocks and why. Prompt instructions are not visible in this way.
- Adding a new blocking rule is a code change: it goes through version control, code review, and appears in the audit log. It does not require prompt tuning or regression testing across all six specialists.
- Behavioral drift across model updates cannot erode compliance enforcement.

### Negative

- Hooks only intercept tool *calls*. A model that skips a required tool call (e.g., fails to call `check_sanctions` at all, reasoning that the entity is "obviously clean") is not caught by a hook. This is a real gap — see Case A-07 in the Adversarial Testing section. Mitigated by: (a) a system prompt instruction that `check_sanctions` is mandatory for every named counterparty without exception, and (b) a post-analysis validation step in the coordinator that checks whether a Compliance agent `WorkstreamAnalysis` contains `sanctions_checked: true`.
- Hook failures (Python exceptions in the hook layer) must be handled explicitly. A hook that crashes defaults to "block and escalate" — not "allow." Fail-closed is the correct policy for a compliance enforcement mechanism.
- The hook layer is Claude Code–specific. Porting the system to a different agent harness requires re-implementing equivalent enforcement in that harness's interception mechanism. This is a migration cost, not an architectural flaw.

---

## Alternatives Rejected

### A. Prompt Instructions Only

Insufficient for compliance-grade guarantees. Model instruction-following is probabilistic. A 99.9% compliance rate on a blocking rule that prevents sanctions violations is not an acceptable target when volume is 200+ intakes per day and each failure has regulatory consequence. Prompt instructions remain as defense-in-depth, not as primary enforcement.

**Rejected as primary enforcement mechanism.**

### B. Pydantic Validation at Tool Input Boundary

Useful and implemented — `route_to_workstream` accepts a typed `RoutingContext` object, and malformed inputs are rejected at the Pydantic boundary. But schema validation validates the *shape* of a tool call, not its *policy compliance*. A perfectly well-formed `route_to_workstream` call with correct types can be a policy violation if deal value exceeds threshold. Pydantic is a correctness tool, not a compliance enforcement tool.

**Implemented as complementary layer; rejected as primary enforcement.**

### C. Post-Hoc Audit and Rollback

Detect violations after the fact and undo routing actions. `route_to_workstream` is explicitly documented as irreversible without manual platform intervention. Post-hoc detection of a sanctions routing violation is substantially worse than pre-emptive blocking — the deal has already been assigned to a workstream team, the clock has started, and reversing the action requires human intervention that is more disruptive than the escalation would have been.

**Rejected.**
