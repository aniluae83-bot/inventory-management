# OrchestratorOne — The Mandate

**For:** Compliance, Legal, and Deal Advisory Leadership  
**Version:** 1.0 — Effective 2026-05-04  
**Maintained by:** Deal Technology Risk function  
**Review cycle:** Quarterly

---

This document defines OrchestratorOne's authority boundary with precision sufficient for governance and legal review. Any behavior outside this mandate is a system defect, not agent judgment. If OrchestratorOne takes an action not described here, that action should be reported as a system failure and investigated accordingly.

The boundaries below are enforced at two independent layers: (1) system prompt instruction, and (2) code-enforced PreToolUse hooks and tool scoping in the agent harness. The code layer is the authoritative enforcement mechanism. Prompt instructions provide defense-in-depth.

---

## What the Agent Decides Alone

OrchestratorOne has autonomous authority over the following decisions, subject to the confidence thresholds and dollar limits below.

**Workstream classification.** Which of the six workstreams — Tax, Legal, Technology, Financial, HR, Compliance — apply to a given intake request. Classification is based on document content and deal metadata as analyzed by the coordinator. All six workstreams are available; the agent determines the applicable subset.

**Priority assignment for low-materiality deals.** For deals below $100M with no sanctions exposure, no FATF-listed jurisdictions, and no document classified as `critical` sensitivity, the agent may assign `low` or `medium` routing priority autonomously. The $100M lower bound maps to the firm's existing partner sign-off policy for material deal commitments; it is an inherited constraint.

**Duplicate detection.** Whether an intake is a probable duplicate of an existing registry entry, based on `lookup_deal_registry` results. This determination is informational — it flags the potential duplicate in the routing record but does not block or modify the intake without human review.

**Specialist subagent sequencing.** Which specialist agents to invoke, in what order, and whether to invoke them in parallel. The coordinator determines sequencing based on document complexity and workstream interdependencies.

**Structured internal follow-up.** Whether to request a missing document or clarification from the intake submitter via a structured internal message to the deal team inbox. The agent may not contact counterparties, co-advisors, or external parties in any form.

---

## What the Agent Escalates

The following categories require human review. The agent must call `escalate_to_human` and must not call `route_to_workstream` when any of these conditions are met. These thresholds are enforced in code; the agent cannot reason past them.

| Escalation Condition | Threshold or Description |
|---------------------|--------------------------|
| Deal value — senior approval required | ≥ $500,000,000 (USD) |
| Deal value expressed as range or with adjustment clauses | Use upper bound; escalate if upper bound indeterminate |
| Sanctions similarity score | ≥ 0.72, including partial name matches |
| Specialist confidence — inconclusive | Any specialist returns confidence < 0.65 |
| Multi-workstream risk trigger | ≥ 3 workstreams independently flag `risk_level: high` or `critical` |
| FATF jurisdiction | Counterparty domiciled in a FATF grey-list or black-list country |
| State-owned enterprise exposure | Counterparty identified as SOE in a restricted jurisdiction |
| Related deal — active conflict | `lookup_deal_registry` returns a related deal with status `under_review` or `blocked` |
| Document sensitivity | Any document classified as `sensitivity: critical` |
| Coordinator loop limit | 8 coordinator turns reached without routing decision |
| Truncated coordinator output | API returns `stop_reason: max_tokens` — a partial analysis must never produce a routing decision |

**Escalation packet contents.** When the agent escalates, the compliance officer receives: the intake summary, all specialist analyses completed, the specific condition that triggered escalation, and a structured description of the decision the reviewer must make. The packet is delivered simultaneously to the compliance officer email list and deal-counsel email list.

**Dollar thresholds origin.** The $500M threshold is the firm's existing internal approval matrix for material deal commitments. The $100M lower bound maps to the existing partner sign-off policy. OrchestratorOne models its authority around these constraints; it did not set them.

---

## What the Agent Must Never Do

These are absolute prohibitions enforced at the code layer. No model reasoning, intake instruction, prompt injection, or runtime configuration can change these behaviors.

**Communicate directly with counterparties, co-advisors, or regulators.** OrchestratorOne has no tool that sends, drafts, queues, or prepares external communications. This is an explicit architectural constraint enforced by tool scoping — the relevant tools do not exist in any agent's tool list. The moment an agent can author external communications, the liability model for the entire system changes in ways that require a separate governance process.

**Clear a sanctions hit without a human override token.** When `check_sanctions` returns a hit — including a partial name match at or above the 0.72 similarity threshold — the pipeline stops. A named, accountable compliance officer must review the finding and provide a signed override via the escalation portal before the pipeline can proceed. This holds even when the agent's confidence that the match is a false positive is high. Clearing a potential sanctions match is a regulated act under OFAC's enforcement framework; in several jurisdictions it carries personal liability for the authorizing individual. A model confidence score cannot satisfy that accountability requirement.

**Route a deal at or above $500M without a logged human approval record.** The PreToolUse hook blocks `route_to_workstream` if `deal_value_usd ≥ $500,000,000`. A human approval token in the session context is required to unblock. The agent prepares the full routing packet and rationale; it does not execute the routing action.

**Modify, summarize, or recharacterize document content.** Documents travel from intake to specialist analysis as-is. The agent may not summarize, paraphrase, extract, or interpret document content before passing it to specialists. Information loss at this stage — a nuance dropped in a summary, a jurisdiction flag omitted in an extraction — is not recoverable.

**Infer deal value from contextual clues when no explicit figure is stated.** If the intake document does not state a deal value, the agent must request clarification or apply the most conservative materiality tier (≥$500M, requiring human approval). This prevents a motivated counterparty from omitting deal value to avoid the $500M block.

**Proceed past 8 coordinator turns without escalating.** The hard loop limit prevents runaway agent loops on ambiguous or adversarially constructed intake documents. At turn 8 without a routing decision, the pipeline escalates automatically regardless of the coordinator's in-progress reasoning.

---

## What We Deliberately Do Not Automate

These are deliberate policy decisions made in consultation with Compliance and Legal leadership. They are not gaps in the system's capability. They should not be revisited without a formal governance review involving the Compliance Officer and General Counsel.

**Final disposition on sanctions hits.** Clearing a potential sanctions match is a regulated act. OrchestratorOne halts the pipeline and packages the finding for human review regardless of the similarity score or the agent's confidence assessment. A model-generated confidence score cannot substitute for the accountability of a named individual making a documented determination.

**Routing approval on deals at or above $500M.** Autonomous routing at this scale would create a decision record inconsistent with fiduciary obligations and, potentially, with the firm's regulatory capital requirements for deal advisory engagements. The agent prepares the full routing packet; a named, accountable individual must confirm it.

**Counterparty risk characterization involving state-owned enterprises or restricted jurisdictions.** Whether a given SOE relationship is a dealbreaker depends on current geopolitical posture, client relationship history, and regulatory guidance that changes faster than any model's training cutoff. The Compliance agent surfaces the flag and retrieves the relevant jurisdiction metadata. It does not characterize the risk or recommend a position.

**Cross-workstream risk synthesis and deal-kill recommendations.** When Tax, Compliance, and HR each independently flag elevated risk, the combined picture may be disqualifying. That conclusion requires a reviewer who can weigh strategic context, client relationships, competitive dynamics, and firm risk appetite — none of which are present in the intake document. OrchestratorOne surfaces the aggregate signal with full specialist reasoning attached. The synthesis is human work.

**All communications external to the firm.** No agent in OrchestratorOne sends, drafts, queues, or prepares messages to counterparties, co-advisors, regulators, or third-party data providers. This is enforced architecturally, not by instruction.

---

## Governance and Threshold Review

This mandate is reviewed quarterly by the Deal Technology Risk function in consultation with the Compliance Officer and General Counsel.

Any proposed change to an authority boundary — including threshold adjustments — requires sign-off from both functions before implementation. Changes must be reflected simultaneously in this document, `config.yaml`, and the agent system prompt. Changes to blocking thresholds additionally require a corresponding update to the PreToolUse hook implementation and a regression run of the adversarial evaluation suite.

Threshold history:

| Parameter | Current Value | Last Reviewed | Approving Party |
|-----------|--------------|---------------|-----------------|
| Materiality — senior approval | $500M | 2026-05-04 | Compliance Officer |
| Materiality — intermediate flag | $100M–$499M | 2026-05-04 | Deal Advisory Leadership |
| Sanctions similarity floor | 0.72 | 2026-05-04 | Compliance Officer |
| Specialist confidence floor | 0.65 | 2026-05-04 | Deal Technology Risk |
| Multi-workstream risk trigger | ≥ 3 at high/critical | 2026-05-04 | Compliance Officer |
| Max coordinator turns | 8 | 2026-05-04 | Deal Technology Risk |

---

*OrchestratorOne v1.0 — Scenario 5 Hackathon Submission — Team OrchestratorOne*  
*Questions: Contact the Deal Technology Risk function.*
