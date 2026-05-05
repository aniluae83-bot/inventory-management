# ADR-001: Coordinator + Specialist Architecture over Single-Agent Monolith

**Status:** Accepted  
**Date:** 2026-05-04  
**Deciders:** Anil Sharma (OrchestratorOne)

---

## Context

OrchestratorOne must analyze M&A intake documents across six distinct professional domains: Tax, Legal, Technology, Financial, HR, and Compliance. Each domain has its own vocabulary, risk signals, regulatory frameworks, and tool requirements.

The initial prototype — `scratch/monolith_attempt.py` — placed all domain reasoning in a single coordinator agent with a unified system prompt. The prompt reached 4,200 tokens with all six domains represented. Testing revealed immediate and reproducible problems:

1. **Cross-domain hallucination.** The monolith conflated Tax jurisdiction flags with Compliance screening requirements, producing hybrid analyses that were incorrect in both domains simultaneously.

2. **Prompt dilution.** Critical domain-specific instructions (e.g., "always call `check_sanctions` before reaching a Compliance conclusion") were buried beneath thousands of tokens of unrelated domain guidance. Instruction-following degraded as prompt length increased — a known and documented behavior.

3. **Non-independent testability.** A bug in the Tax domain reasoning could not be isolated without running the full six-domain context. Every test required the entire monolith to be live. A failing Compliance assertion broke the Tax test suite.

4. **Unscoped tool access.** A single agent with access to all tools could, in principle, call `route_to_workstream` from within what was conceptually a "Compliance check" — making the authority model implicit and unauditable. There was no code boundary between analysis and routing.

5. **Prompt iteration risk.** Tightening one domain's instructions risked degrading another. The Compliance agent prompt went through six revisions; in a monolith, each revision would have required re-validating all six domains.

---

## Decision

Adopt a **coordinator + specialist pattern**:

- **One coordinator agent** receives the intake, determines which workstreams apply, spawns specialists, aggregates their structured outputs, and makes the final routing or escalation decision. It performs no domain-specific analysis.
- **Six specialist agents** (Tax, Legal, Technology, Financial, HR, Compliance) each receive their domain's slice of the intake and produce a typed `WorkstreamAnalysis` struct. Each has a focused system prompt under 800 tokens and only the tools their workstream legitimately needs.

The coordinator and each specialist are independent Claude API sessions — they share no context window. Specialists run in parallel where intake complexity permits.

---

## Consequences

### Positive

- Each specialist prompt is under 800 tokens. Cross-domain confusion is architecturally impossible — a Tax agent cannot see Compliance tool definitions, cannot see Compliance's system prompt, and cannot call `check_sanctions`.
- Specialists are independently testable. A failing Compliance test does not require running Tax, Legal, or Financial logic. Test suites mirror the agent structure 1:1.
- Tool scoping is explicit and auditable. The capability table in `CLAUDE.md` is the single source of truth for what each agent can do. A compliance auditor reading that table understands the authority model without reading Python.
- Parallel specialist execution reduces wall-clock time for multi-workstream intakes.
- Prompt iteration is safe per-workstream. Revising the Compliance specialist's system prompt carries no risk to Tax specialist behavior.

### Negative

- Six specialist API calls per intake add latency if run serially. Mitigated by parallel dispatch in the coordinator loop.
- The coordinator's context does not contain raw specialist reasoning — it receives structured `WorkstreamAnalysis` objects. If a specialist's internal reasoning matters for audit, it must be explicitly included in the output struct. It is — the `rationale` field is required and non-nullable.
- Maintaining six system prompts is more overhead than one. Accepted: the per-prompt quality gain outweighs maintenance cost. Prompt changes are small-scope code changes that go through review.
- Coordinator cannot see the document text directly after specialist dispatch — it works from structured tool outputs. This is intentional (prevents direct prompt injection from document content into coordinator context) but means the coordinator's routing rationale is only as good as specialist `WorkstreamAnalysis` structs.

---

## Alternatives Rejected

### A. Monolith with Extended Context Window

Increasing the context window does not solve prompt dilution. Instructions compete for model attention regardless of window size. The hallucination rate on jurisdiction-specific Tax questions remained elevated even at lower prompt lengths when domain content was interleaved with other domains. The problem is attention distribution, not token count.

**Rejected.**

### B. Single Agent with Tool-Based Domain Delegation

One agent, six "domain tools" that each execute a sub-prompt internally. Reduces cross-domain confusion in the main context but keeps routing authority and domain analysis in the same agent session — making the scoped authority model impossible to enforce deterministically. The agent could call `route_to_workstream` from within the same turn as a "compliance analysis" sub-call. Authority boundaries would be prompt-enforced rather than code-enforced.

**Rejected.**

### C. Chained Sequential Pipeline

Specialists run sequentially, each receiving the prior specialist's output in addition to the intake. Eliminates the coordination overhead but doubles or triples wall-clock time. Also creates information contamination risk: a Legal agent whose output includes erroneous framing could influence the Financial agent's analysis of the same document downstream. The cascade failure mode is worse than the coordination overhead.

**Rejected.**

### D. Hierarchical Specialists with Sub-Specialists

Tax agent spawns its own sub-agents (domestic tax, international tax, transfer pricing). Explored briefly. The marginal gain in domain precision did not justify the additional orchestration complexity for the scope of this system. Could be revisited if individual workstreams prove to have materially different reasoning profiles across deal types.

**Not adopted in v1 — deferred.**
