"""
OrchestratorOne — PreToolUse Hook Enforcement Layer
All three compliance-critical blocking rules. Nothing else lives here.

Hooks are evaluated against source deal data and runtime session state —
never against model-generated fields. An agent cannot reason past a hook.
"""
from __future__ import annotations

MATERIALITY_THRESHOLD_USD = 500_000_000   # sourced from firm's internal approval matrix
SANCTIONS_SIMILARITY_FLOOR = 0.72         # OFAC partial name match calibration


def pre_tool_use_hook(
    tool_name: str,
    tool_input: dict,
    deal_value_usd: float,
    session_ctx: dict,
) -> dict | None:
    """
    Evaluate a pending tool call against all three blocking rules.

    Parameters
    ----------
    tool_name : str
        The tool the agent is about to call.
    tool_input : dict
        The tool's input arguments (logged but not used for policy evaluation).
    deal_value_usd : float
        From the validated IntakeRequest — NOT from any model-generated field.
    session_ctx : dict
        Runtime state for this intake session:
            sanctions_hits_found (bool): set when any specialist finds a sanctions match
            human_override_token (str | None): set when a named approver grants override

    Returns
    -------
    dict
        Block record with keys: blocked, rule, reason, action_required.
        Returns None if the tool call is permitted.
    """

    # ── Rule 1 ─────────────────────────────────────────────────────────────────
    # Block route_to_workstream on material deals without senior approval.
    # Enforcement: source deal value from IntakeRequest, not from model output.
    if tool_name == "route_to_workstream":
        if deal_value_usd >= MATERIALITY_THRESHOLD_USD:
            if not session_ctx.get("human_override_token"):
                return {
                    "blocked": True,
                    "rule": "materiality_threshold",
                    "reason": (
                        f"Deal value ${deal_value_usd:,.0f} meets or exceeds the "
                        f"${MATERIALITY_THRESHOLD_USD:,.0f} materiality threshold. "
                        "Senior partner sign-off is required before routing. "
                        "This block is code-enforced and cannot be bypassed by model reasoning."
                    ),
                    "action_required": (
                        "Obtain named senior partner approval via the escalation portal. "
                        "Resubmit with a human_override_token once approval is recorded."
                    ),
                }

    # ── Rule 2 ─────────────────────────────────────────────────────────────────
    # Block route_to_workstream if any sanctions hit was detected in this session.
    # Enforcement: session_ctx is written by the coordinator when specialist results
    # contain a sanctions hit — not by the model's routing_rationale field.
    if tool_name == "route_to_workstream":
        if session_ctx.get("sanctions_hits_found"):
            return {
                "blocked": True,
                "rule": "sanctions_hit",
                "reason": (
                    "A sanctions match was detected in this session. "
                    "Routing is blocked until a named compliance officer reviews the finding "
                    "and provides a signed override token. "
                    "Clearing a sanctions match is a regulated act — "
                    "model confidence cannot substitute for individual accountability."
                ),
                "action_required": (
                    "Compliance officer must review the sanctions finding via the escalation portal "
                    "and provide a signed override token. "
                    "Do not clear based on legal-form suffix (GmbH, OOO, LLC) or jurisdiction "
                    "inference alone — these do not establish entity distinctness under OFAC guidance."
                ),
            }

    # ── Rule 3 ─────────────────────────────────────────────────────────────────
    # Block check_sanctions itself on material deals without prior human approval.
    # Rationale: on a $500M+ deal, even initiating a sanctions check without senior
    # partner awareness creates a documentation gap in the approval chain.
    if tool_name == "check_sanctions":
        if deal_value_usd >= MATERIALITY_THRESHOLD_USD:
            if not session_ctx.get("human_override_token"):
                return {
                    "blocked": True,
                    "rule": "sanctions_check_materiality",
                    "reason": (
                        f"Deal value ${deal_value_usd:,.0f} exceeds the "
                        f"${MATERIALITY_THRESHOLD_USD:,.0f} materiality threshold. "
                        "Senior partner approval is required before initiating a "
                        "sanctions screening on a material deal."
                    ),
                    "action_required": (
                        "Obtain senior partner acknowledgment before sanctions screening. "
                        "The screening result will be included in the partner's routing decision packet."
                    ),
                }

    return None
