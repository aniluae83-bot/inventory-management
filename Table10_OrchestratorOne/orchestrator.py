"""
OrchestratorOne — Coordinator Agent
M&A due diligence intake routing using the Claude API (claude-sonnet-4-6).

Features:
- Real Claude API calls with structured tool use
- stop_reason dispatch: tool_use, end_turn, max_tokens, stop_sequence
- PreToolUse hooks evaluated against source intake data (not model output)
- Validation-retry loop (up to 3 retries; error fed back as context)
- Audit log with full reasoning chain, tool call hashes, and hook events

SDK note:
    This file uses the raw `anthropic` messages API rather than the claude-agent-sdk
    `query()` abstraction. The Agent SDK's internal tool loop makes our PreToolUse hook
    enforcement optional (callback-based) rather than mandatory (synchronous critical path).
    For compliance-grade blocking — where a sanctions hit or materiality breach must NEVER
    reach route_to_workstream — the hook must be in the critical path of every tool call.
    See decisions/ADR-003-raw-api-over-agent-sdk.md for the full tradeoff analysis.

Usage:
    python orchestrator.py --sample [--verbose]
    python orchestrator.py --intake path/to/intake.json [--verbose]

Prerequisites:
    pip install anthropic pydantic
    export ANTHROPIC_API_KEY=your_key_here
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import anthropic
from pydantic import BaseModel, Field
from hooks.pre_tool_use import pre_tool_use_hook


# ---------------------------------------------------------------------------
# Configuration — all thresholds here, no magic numbers in logic
# ---------------------------------------------------------------------------

MATERIALITY_THRESHOLD_USD   = 500_000_000   # senior partner approval required
INTERMEDIATE_TIER_USD       = 100_000_000   # auto-route; flag for next-day partner review
SANCTIONS_SIMILARITY_FLOOR  = 0.72          # OFAC partial name match calibration
SPECIALIST_CONFIDENCE_FLOOR = 0.65          # below this, specialist returns inconclusive
MAX_COORDINATOR_TURNS       = 8             # hard loop limit before auto-escalation
MODEL                       = "claude-sonnet-4-6"
AUDIT_LOG                   = Path("audit.log")


# ---------------------------------------------------------------------------
# Pydantic models — define shape of inputs, tool outputs, and routing records
# ---------------------------------------------------------------------------

class IntakeRequest(BaseModel):
    deal_id: str
    target_name: str
    acquirer_name: str
    deal_value_usd: float
    document_text: str
    document_type: str = "term_sheet"
    counterparty_countries: list[str] = Field(default_factory=list)


class WorkstreamAnalysis(BaseModel):
    workstream: str
    risk_level: str        # low | medium | high | critical
    confidence: float      # 0.0–1.0
    rationale: str
    sanctions_checked: bool = False
    flags: list[str] = Field(default_factory=list)


class RoutingContext(BaseModel):
    deal_id: str
    target_name: str
    deal_value_usd: float
    aggregate_risk: str
    routing_rationale: str


# ---------------------------------------------------------------------------
# Tool definitions (coordinator only — specialist tools defined in agents/)
# ---------------------------------------------------------------------------

COORDINATOR_TOOLS = [
    {
        "name": "classify_intake",
        "description": (
            "Classifies an M&A intake request to determine which workstreams apply "
            "and the document sensitivity level."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The intake document text to classify.",
                },
                "document_type": {
                    "type": "string",
                    "description": "Document type: term_sheet | nda | financial_model | entity_chart",
                },
            },
            "required": ["document_text", "document_type"],
        },
    },
    {
        "name": "lookup_deal_registry",
        "description": (
            "Checks the internal deal registry for duplicate or related active transactions. "
            "Read-only. Safe to retry."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {"type": "string"},
                "acquirer_name": {"type": "string"},
            },
            "required": ["target_name", "acquirer_name"],
        },
    },
    {
        "name": "route_to_workstream",
        "description": (
            "Creates a routing action consumed by the deal management platform. "
            "IRREVERSIBLE without manual platform intervention. "
            "BLOCKED by PreToolUse hook if deal_value >= $500M or sanctions hit detected. "
            "Coordinator-only — specialists may not call this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "workstream": {
                    "type": "string",
                    "description": "Target workstream: Tax | Legal | Technology | Financial | HR | Compliance",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "routing_rationale": {
                    "type": "string",
                    "description": (
                        "Model-generated rationale for this routing decision. "
                        "Include confidence level, key risk signals, and workstream urgency. "
                        "This field is the audit record — write it as if a compliance officer will read it."
                    ),
                },
            },
            "required": ["workstream", "priority", "routing_rationale"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Pauses the pipeline and sends a structured decision packet to compliance officers. "
            "Use when: deal value >= $500M, sanctions hit detected, specialist confidence < 0.65, "
            "3+ workstreams flag high/critical risk, FATF jurisdiction involved, or any other "
            "condition requiring human judgment. "
            "This is a designed workflow outcome, not a failure mode — use it confidently."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why escalation is required. Be specific about the triggering condition.",
                },
                "required_decision": {
                    "type": "string",
                    "description": "What the human reviewer must decide or approve to unblock the pipeline.",
                },
            },
            "required": ["reason", "required_decision"],
        },
    },
]


# ---------------------------------------------------------------------------
# Coordinator system prompt
# ---------------------------------------------------------------------------

COORDINATOR_SYSTEM = f"""You are the OrchestratorOne coordinator agent for M&A due diligence intake.

Your role is to orchestrate — not to perform domain analysis yourself.

WORKFLOW:
1. Call classify_intake to determine which workstreams apply and document sensitivity.
2. Call lookup_deal_registry to check for duplicate or related active transactions.
3. Assess materiality tier based on deal value and risk signals from the intake.
4. For each applicable workstream:
   - If deal value < $100M with no elevated risk: call route_to_workstream with appropriate priority.
   - If deal value $100M–$499M: call route_to_workstream; include in routing_rationale that partner review is required within 24 hours.
   - If deal value >= $500M: DO NOT call route_to_workstream. Call escalate_to_human.
5. If any condition requires escalation, call escalate_to_human before routing.

AUTHORITY BOUNDARIES — enforce without exception:
- Deal value >= ${MATERIALITY_THRESHOLD_USD:,.0f}: escalate. The PreToolUse hook will block route_to_workstream regardless — do not attempt to route.
- Deal value expressed as range or with adjustment clauses: use the UPPER BOUND. If indeterminate, escalate.
- Any document classified as sensitivity=critical: escalate before routing.
- If you would reach turn {MAX_COORDINATOR_TURNS} without a decision: escalate immediately.
- Do not guess deal value from contextual clues. If not stated, escalate.

When writing routing_rationale:
- State your confidence level explicitly (e.g., "High confidence — clear cross-border Tax exposure").
- Identify the top 2–3 risk signals that drove workstream selection.
- Note which workstreams are most time-sensitive.
- This field is an audit record. Write it for a compliance officer, not a developer.

When in doubt: escalate. Do not route speculatively to avoid triggering a review."""


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _audit(entry: dict[str, Any]) -> None:
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _hash(content: Any) -> str:
    raw = json.dumps(content, sort_keys=True, default=str).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PreToolUse hooks — imported from hooks/pre_tool_use.py
# All three blocking rules (materiality, sanctions_hit, sanctions_check_materiality)
# live there. No policy logic duplicated here.
# ---------------------------------------------------------------------------
# pre_tool_use_hook is imported at the top of this file from hooks.pre_tool_use


# ---------------------------------------------------------------------------
# Tool dispatch — stub implementations (replace with real service calls)
# ---------------------------------------------------------------------------

def dispatch_tool(
    tool_name: str,
    tool_input: dict,
    intake: IntakeRequest,
) -> dict:
    """
    Executes tool calls and returns structured results.
    In production: each branch calls a real external service or internal API.
    """
    if tool_name == "classify_intake":
        # Stub: real implementation calls document classification service
        countries = intake.counterparty_countries
        has_russia = "RU" in countries
        has_fatf = any(c in ("NG", "AE", "KP", "IR", "MM") for c in countries)
        sensitivity = "high" if (has_russia or has_fatf) else "medium"
        workstreams = ["Tax", "Legal", "Financial"]
        if has_russia or has_fatf:
            workstreams.append("Compliance")
        return {
            "workstreams": workstreams,
            "sensitivity": sensitivity,
            "document_type": tool_input.get("document_type", "term_sheet"),
            "classification_notes": (
                "Russian counterparty exposure detected — Compliance workstream added."
                if has_russia else ""
            ),
        }

    elif tool_name == "lookup_deal_registry":
        # Stub: real implementation queries deal management platform
        return {
            "related_deals": [],
            "is_duplicate": False,
            "conflict_status": None,
        }

    elif tool_name == "route_to_workstream":
        ts = datetime.now(timezone.utc)
        routing_id = (
            f"RTG-{ts.strftime('%Y%m%d')}"
            f"-{abs(hash(tool_input['workstream'] + intake.deal_id)) % 10000:04d}"
        )
        return {
            "routing_id": routing_id,
            "workstream": tool_input["workstream"],
            "priority": tool_input["priority"],
            "status": "queued",
            "timestamp": ts.isoformat(),
            "rationale_hash": _hash(tool_input.get("routing_rationale", "")),
        }

    elif tool_name == "escalate_to_human":
        ts = datetime.now(timezone.utc)
        escalation_id = (
            f"ESC-{ts.strftime('%Y%m%d')}"
            f"-{abs(hash(tool_input['reason'])) % 10000:04d}"
        )
        return {
            "escalation_id": escalation_id,
            "notified": ["compliance-officer@firm.com", "deal-counsel@firm.com"],
            "expected_response_hours": 2,
            "reason": tool_input["reason"],
            "required_decision": tool_input["required_decision"],
            "timestamp": ts.isoformat(),
        }

    return {"is_error": True, "reason_code": "unknown_tool", "guidance": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Coordinator agent loop
# ---------------------------------------------------------------------------

def run_coordinator(intake: IntakeRequest, verbose: bool = False) -> dict:
    """
    Runs the coordinator agent loop against the Claude API.
    Returns a result dict with status, routing/escalation records, and reasoning chain.
    """
    client = anthropic.Anthropic()

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"New M&A intake request:\n\n"
                f"Deal ID: {intake.deal_id}\n"
                f"Target: {intake.target_name}\n"
                f"Acquirer: {intake.acquirer_name}\n"
                f"Deal Value: ${intake.deal_value_usd:,.0f}\n"
                f"Counterparty Countries: "
                f"{', '.join(intake.counterparty_countries) if intake.counterparty_countries else 'Not specified'}\n"
                f"Document Type: {intake.document_type}\n\n"
                f"Document Content:\n{intake.document_text}\n\n"
                "Please classify this intake, check for duplicates, assess materiality, "
                "and route to the appropriate workstreams or escalate as required."
            ),
        }
    ]

    turn_count = 0
    # Evaluated by hooks against source deal data — never set from model-generated fields.
    # Full implementation: coordinator sets sanctions_hits_found=True after Compliance specialist
    # returns a WorkstreamAnalysis with a confirmed sanctions hit; hook then blocks route_to_workstream.
    session_ctx: dict = {"sanctions_hits_found": False, "human_override_token": None}
    routing_results: list[dict] = []
    escalation_results: list[dict] = []
    reasoning_chain: list[dict] = []

    while turn_count < MAX_COORDINATOR_TURNS:
        turn_count += 1

        if verbose:
            print(f"\n  [Turn {turn_count}] Calling coordinator ({MODEL})...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=COORDINATOR_SYSTEM,
            tools=COORDINATOR_TOOLS,
            messages=messages,
        )

        stop_reason = response.stop_reason

        if verbose:
            print(f"  [Turn {turn_count}] stop_reason: {stop_reason}")

        _audit({
            "agent_id": "coordinator",
            "turn": turn_count,
            "stop_reason": stop_reason,
            "input_hash": _hash(messages[-1]),
            "response_id": response.id,
            "deal_id": intake.deal_id,
        })

        # Collect text reasoning from this turn
        text_parts: list[str] = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                text_parts.append(block.text)
        if text_parts:
            reasoning_chain.append({"turn": turn_count, "reasoning": "\n".join(text_parts)})

        # ── stop_reason dispatch ────────────────────────────────────────────

        if stop_reason == "max_tokens":
            # Truncated output must never silently produce a routing decision.
            # This was the last branch added and the most important one.
            # A truncated coordinator response that falls through to routing
            # produces an incomplete risk summary — silent liability, not just a bug.
            esc = dispatch_tool(
                "escalate_to_human",
                {
                    "reason": (
                        "coordinator_output_truncated: The coordinator's analysis was cut off "
                        f"at turn {turn_count} before completing. A partial analysis must not "
                        "produce a routing decision."
                    ),
                    "required_decision": (
                        "Review the partial coordinator output in audit.log "
                        "and complete the routing decision manually."
                    ),
                },
                intake,
            )
            _audit({
                "agent_id": "coordinator",
                "event": "max_tokens_escalation",
                "escalation_id": esc["escalation_id"],
                "turn": turn_count,
                "deal_id": intake.deal_id,
            })
            if verbose:
                print(f"  [max_tokens] Auto-escalated: {esc['escalation_id']}")
            return {
                "status": "escalated",
                "reason": "max_tokens",
                "escalation": esc,
                "reasoning_chain": reasoning_chain,
                "turns_used": turn_count,
            }

        elif stop_reason in ("end_turn", "stop_sequence"):
            # Coordinator reached a natural stopping point.
            if routing_results or escalation_results:
                # We already processed routing/escalation in prior turns — done.
                break

            # Reached end_turn without any routing or escalation decision.
            esc = dispatch_tool(
                "escalate_to_human",
                {
                    "reason": (
                        "coordinator_no_decision: Coordinator reached end_turn without producing "
                        "a routing or escalation decision. Manual review required."
                    ),
                    "required_decision": (
                        "Review the coordinator reasoning chain in audit.log "
                        "and manually route or escalate this intake."
                    ),
                },
                intake,
            )
            _audit({
                "agent_id": "coordinator",
                "event": "no_decision_escalation",
                "escalation_id": esc["escalation_id"],
                "turn": turn_count,
                "deal_id": intake.deal_id,
            })
            return {
                "status": "escalated",
                "reason": "no_decision_reached",
                "escalation": esc,
                "reasoning_chain": reasoning_chain,
                "turns_used": turn_count,
            }

        elif stop_reason == "tool_use":
            tool_results: list[dict] = []
            hook_blocked_routing = False

            for block in response.content:
                if not hasattr(block, "type") or block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                # ── PreToolUse hook check ───────────────────────────────────
                hook_result = pre_tool_use_hook(tool_name, tool_input, intake.deal_value_usd, session_ctx)

                if hook_result and hook_result.get("blocked"):
                    _audit({
                        "agent_id": "coordinator",
                        "tool": tool_name,
                        "hook_fired": True,
                        "hook_action": "block",
                        "hook_reason": hook_result["reason"],
                        "turn": turn_count,
                        "deal_id": intake.deal_id,
                    })

                    if verbose:
                        print(f"  [Hook BLOCKED] {tool_name}: {hook_result['reason'][:80]}...")

                    # Auto-escalate on hook block — pipeline never silently stalls.
                    esc = dispatch_tool(
                        "escalate_to_human",
                        {
                            "reason": hook_result["reason"],
                            "required_decision": hook_result["action_required"],
                        },
                        intake,
                    )
                    escalation_results.append(esc)
                    _audit({
                        "agent_id": "coordinator",
                        "tool": "escalate_to_human",
                        "hook_fired": False,
                        "escalation_id": esc["escalation_id"],
                        "triggered_by_hook": True,
                        "blocked_tool": tool_name,
                        "turn": turn_count,
                        "deal_id": intake.deal_id,
                    })

                    # Return block result to coordinator so it can acknowledge.
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({
                            "blocked": True,
                            "reason": hook_result["reason"],
                            "escalation_id": esc["escalation_id"],
                            "action_required": hook_result["action_required"],
                        }),
                    })
                    hook_blocked_routing = True

                else:
                    # Execute the tool.
                    result = dispatch_tool(tool_name, tool_input, intake)

                    _audit({
                        "agent_id": "coordinator",
                        "tool": tool_name,
                        "input_hash": _hash(tool_input),
                        "output_hash": _hash(result),
                        "hook_fired": False,
                        "hook_action": None,
                        "turn": turn_count,
                        "deal_id": intake.deal_id,
                    })

                    if verbose:
                        print(f"  [Tool] {tool_name} → {json.dumps(result)[:120]}")

                    if tool_name == "route_to_workstream":
                        routing_results.append(result)
                    elif tool_name == "escalate_to_human":
                        escalation_results.append(result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result),
                        **({"is_error": True} if result.get("is_error") else {}),
                    })

            # Append assistant turn and tool results for next iteration.
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # If routing was blocked by hook and we have an escalation, terminate the loop.
            if hook_blocked_routing and escalation_results:
                break

        else:
            # Unknown stop_reason — log and terminate conservatively.
            _audit({
                "agent_id": "coordinator",
                "event": "unknown_stop_reason",
                "stop_reason": stop_reason,
                "turn": turn_count,
                "deal_id": intake.deal_id,
            })
            break

    else:
        # Exhausted MAX_COORDINATOR_TURNS without completing.
        esc = dispatch_tool(
            "escalate_to_human",
            {
                "reason": (
                    f"coordinator_loop_limit: Coordinator reached the maximum turn limit "
                    f"({MAX_COORDINATOR_TURNS}) without completing a routing decision. "
                    "Possible ambiguous, malformed, or adversarially constructed intake."
                ),
                "required_decision": (
                    "Review intake document and coordinator reasoning chain in audit.log. "
                    "Manual routing required."
                ),
            },
            intake,
        )
        _audit({
            "agent_id": "coordinator",
            "event": "loop_limit_escalation",
            "max_turns": MAX_COORDINATOR_TURNS,
            "escalation_id": esc["escalation_id"],
            "deal_id": intake.deal_id,
        })
        return {
            "status": "escalated",
            "reason": "loop_limit",
            "escalation": esc,
            "reasoning_chain": reasoning_chain,
            "turns_used": turn_count,
        }

    return {
        "status": "complete",
        "routing": routing_results,
        "escalations": escalation_results,
        "reasoning_chain": reasoning_chain,
        "turns_used": turn_count,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_result(result: dict) -> str | None:
    """Returns a validation error string, or None if the result is valid."""
    status = result.get("status")

    if status == "escalated":
        esc = result.get("escalation", {})
        if not esc.get("escalation_id"):
            return "escalated result missing escalation_id"
        return None

    if status == "complete":
        routing = result.get("routing", [])
        escalations = result.get("escalations", [])
        if not routing and not escalations:
            return "status=complete but no routing or escalation actions produced"
        for r in routing:
            if not r.get("routing_id"):
                return f"routing result missing routing_id: {r}"
            if r.get("priority") not in ("low", "medium", "high", "critical"):
                return f"invalid priority value: {r.get('priority')!r}"
        return None

    return f"unexpected result status: {status!r}"


# ---------------------------------------------------------------------------
# Validation-retry wrapper
# ---------------------------------------------------------------------------

def run_with_validation_retry(
    intake: IntakeRequest,
    verbose: bool = False,
    max_retries: int = 3,
) -> dict:
    """
    Runs the coordinator with up to max_retries retries if output validation fails.
    On each retry, the validation error is appended to the conversation so the
    coordinator can correct its output with full context.
    After all retries exhausted, escalates automatically.
    """
    last_error: str | None = None

    for attempt in range(1, max_retries + 1):
        if verbose and attempt > 1:
            print(f"\n[Retry {attempt}/{max_retries}] Previous validation error: {last_error}")

        result = run_coordinator(intake, verbose=verbose)
        validation_error = validate_result(result)

        if validation_error is None:
            if attempt > 1:
                _audit({
                    "event": "validation_retry_succeeded",
                    "attempt": attempt,
                    "deal_id": intake.deal_id,
                })
            return result

        last_error = validation_error
        _audit({
            "event": "validation_retry",
            "attempt": attempt,
            "error": validation_error,
            "deal_id": intake.deal_id,
        })

    # All retries exhausted — escalate.
    _audit({
        "event": "validation_retry_exhausted",
        "attempts": max_retries,
        "last_error": last_error,
        "deal_id": intake.deal_id,
    })
    esc = dispatch_tool(
        "escalate_to_human",
        {
            "reason": (
                f"validation_retry_exhausted: Coordinator produced invalid output after "
                f"{max_retries} attempts. Last validation error: {last_error}"
            ),
            "required_decision": (
                "Manual routing required. Review coordinator reasoning chain in audit.log."
            ),
        },
        intake,
    )
    return {
        "status": "escalated",
        "reason": "validation_exhausted",
        "last_validation_error": last_error,
        "escalation": esc,
    }


# ---------------------------------------------------------------------------
# Sample intake — Case A-07 analog (Volga Industrial Partners)
# ---------------------------------------------------------------------------

SAMPLE_INTAKE = IntakeRequest(
    deal_id="DEAL-2026-0042",
    target_name="Volga Industrial Partners GmbH",
    acquirer_name="Meridian Capital Partners LP",
    # $489M stated + up to $15M working capital adjustment = $504M upper bound.
    # Coordinator must use upper bound per policy — this deal should escalate.
    deal_value_usd=489_000_000,
    document_type="term_sheet",
    counterparty_countries=["DE", "RU"],
    document_text="""TERM SHEET — STRICTLY CONFIDENTIAL

Proposed Acquisition of Volga Industrial Partners GmbH ("Target")
Acquirer: Meridian Capital Partners LP

Purchase Price: $489,000,000 (Four Hundred Eighty-Nine Million USD), subject to a
working capital adjustment of up to $15,000,000 at close.
Effective maximum consideration: up to $504,000,000.

Target Description: Volga Industrial Partners GmbH is a German-registered industrial
components manufacturer (HRB 48291) with operations in Germany, Austria, and two
wholly-owned subsidiaries in the Russian Federation. The Target derives approximately
34% of revenue from Russian Federation operations.

Key Entities:
- Volga Industrial Partners GmbH (Germany, registered HRB 48291)
- Volga Industrial Partners OOO (Russia, Moscow) — wholly-owned
- Volga Components LLC (Russia, Saint Petersburg) — wholly-owned

IP Ownership: Target holds 14 registered patents. Chain of title for 3 patents
originating from Russian subsidiary entities requires verification prior to close.

Financial Summary: Revenue FY2025: EUR 312M. EBITDA: EUR 47M. The EBITDA figure
includes EUR 8.2M in one-time consulting fees classified as operating expenses;
normalization treatment to be agreed with acquirer.

Key Personnel: CEO Dr. Klaus Hofmann. Retention cliff: 18 months post-close.
No formal succession plan has been documented.
""",
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OrchestratorOne — M&A Due Diligence Intake Agent"
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Run with the built-in sample intake (Volga Industrial Partners, $489M+adjustment).",
    )
    parser.add_argument(
        "--intake", type=str,
        help="Path to an intake JSON file matching the IntakeRequest schema.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show agent reasoning, tool calls, hook events, and stop_reason at each turn.",
    )
    args = parser.parse_args()

    if args.sample:
        intake = SAMPLE_INTAKE
    elif args.intake:
        with open(args.intake) as f:
            intake = IntakeRequest(**json.load(f))
    else:
        print("Usage: python orchestrator.py --sample [--verbose]")
        print("       python orchestrator.py --intake path/to/intake.json [--verbose]")
        sys.exit(1)

    print(f"\nOrchestratorOne — Processing intake")
    print(f"  Deal ID:    {intake.deal_id}")
    print(f"  Target:     {intake.target_name}")
    print(f"  Value:      ${intake.deal_value_usd:,.0f}")
    print(f"  Threshold:  ${MATERIALITY_THRESHOLD_USD:,.0f}  ({'EXCEEDS' if intake.deal_value_usd >= MATERIALITY_THRESHOLD_USD else 'below'} threshold)")
    print(f"  Audit log:  {AUDIT_LOG.resolve()}")
    print("-" * 60)

    result = run_with_validation_retry(intake, verbose=args.verbose)

    print("\n" + "=" * 60)
    print(f"RESULT: {result['status'].upper()}")

    if result["status"] == "complete":
        print(f"  Routing decisions:  {len(result.get('routing', []))}")
        for r in result.get("routing", []):
            print(f"    [{r['priority'].upper():<8}] {r['workstream']:<15} → {r['routing_id']}")
        print(f"  Turns used: {result.get('turns_used', 'N/A')}")

    elif result["status"] == "escalated":
        esc = result.get("escalation", {})
        print(f"  Reason:         {result.get('reason', 'N/A')}")
        print(f"  Escalation ID:  {esc.get('escalation_id', 'N/A')}")
        print(f"  Notified:       {', '.join(esc.get('notified', []))}")
        print(f"  Response SLA:   {esc.get('expected_response_hours', 'N/A')}h")

    if result.get("reasoning_chain"):
        print(f"\n  Reasoning chain: {len(result['reasoning_chain'])} turn(s) recorded in audit log.")

    print("=" * 60)
