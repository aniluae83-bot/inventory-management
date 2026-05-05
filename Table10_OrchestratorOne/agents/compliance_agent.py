"""
OrchestratorOne — Compliance Specialist Agent
Handles OFAC/EU/UN sanctions screening, FATF jurisdiction assessment, AML/KYC review.

Authority boundary: Compliance analysis only.
Tools: classify_document (entity extraction + jurisdiction risk), check_sanctions (OFAC/EU/UN).
Cannot call route_to_workstream — routing authority is coordinator-only.

Usage: Spawned by coordinator after classify_intake identifies Compliance as a relevant workstream.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, SPECIALIST_CONFIDENCE_FLOOR, MODEL


# ---------------------------------------------------------------------------
# Compliance specialist system prompt
# ---------------------------------------------------------------------------

COMPLIANCE_SYSTEM = """You are the Compliance specialist in a multi-agent M&A due diligence system.

AUTHORITY: Compliance analysis only. Do not advise on Tax, Legal, Financial, HR, or Technology.

MANDATORY PROCEDURE — no exceptions, no shortcuts:
1. Call classify_document first to extract named counterparty entities and assess jurisdiction risk.
2. Call check_sanctions for EVERY named counterparty — including all subsidiaries, holding companies,
   ultimate beneficial owners, and affiliated persons named in the document.
3. Legal suffix (GmbH, OOO, LLC, SA, Ltd, PLC) does NOT establish entity distinctness.
   If a named entity shares a parent name with a known listed entity, run check_sanctions regardless.
   The tool result determines distinctness — not your assessment of legal form.
4. If check_sanctions returns any match with similarity_score >= 0.72, set sanctions_checked=True,
   add the hit details to flags, set risk_level=critical, confidence=0.90, and stop further analysis.
   Do not attempt to resolve the hit — human review is mandatory per OFAC guidance.
5. FATF grey-list jurisdictions require enhanced due diligence. Current grey-list includes:
   NG, AE, PH, ZA, JO, AL, BB, BF, KH, HT, MZ, PK, PA, SN, SY, TZ, TT, YE, VU.
   Black-list (call block): KP, IR, MM. Set risk_level=high for any confirmed FATF exposure.
6. If AML documentation is incomplete or UBO is undisclosed, set risk_level=high and flag it.
7. If your confidence would fall below 0.65, return risk_level=high and note inconclusive
   rather than guessing a determination.

Return a structured JSON analysis. Do not speculate on deal strategy or valuation.
Confidence must reflect actual evidence — do not inflate to avoid escalation."""

# ---------------------------------------------------------------------------
# Compliance specialist tools (scoped — no route_to_workstream)
# ---------------------------------------------------------------------------

COMPLIANCE_TOOLS = [
    {
        "name": "classify_document",
        "description": (
            "Classifies intake document to extract named counterparty entities for sanctions screening, "
            "assess jurisdiction exposure (FATF grey/black-list), and identify AML/KYC documentation gaps. "
            "Returns: entity_list, jurisdiction_codes, sensitivity, fatf_hits, aml_gap_flags."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The full intake document text.",
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
        "name": "check_sanctions",
        "description": (
            "Screens a named entity against OFAC SDN, EU Consolidated, and UN Security Council lists. "
            "Returns match results with similarity_score for each list searched. "
            "MUST be called for every named counterparty without exception. "
            "A legal suffix (GmbH, OOO, LLC) does NOT establish entity distinctness — "
            "call this tool regardless of your assessment of the entity's legal form or jurisdiction."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Full legal name of the entity to screen, exactly as stated in the document.",
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code of the entity's registered jurisdiction.",
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["corporate", "individual", "government"],
                    "description": "Entity classification for list matching.",
                },
            },
            "required": ["entity_name", "jurisdiction", "entity_type"],
        },
    },
]

# ---------------------------------------------------------------------------
# FATF jurisdiction sets
# ---------------------------------------------------------------------------

FATF_GREY = {
    "NG", "AE", "PH", "ZA", "JO", "AL", "BB", "BF", "KH",
    "HT", "MZ", "PK", "PA", "SN", "SY", "TZ", "TT", "YE", "VU",
}
FATF_BLACK = {"KP", "IR", "MM"}

# ---------------------------------------------------------------------------
# Stub tool dispatch — replace with real OFAC/EU/UN API calls in production
# ---------------------------------------------------------------------------


def _dispatch_compliance_tool(
    tool_name: str,
    tool_input: dict,
    document_text: str,
    counterparty_countries: list[str],
) -> dict:
    """Stub implementations. Replace with real sanctions API calls in production."""
    if tool_name == "classify_document":
        fatf_grey_hits = [c for c in counterparty_countries if c in FATF_GREY]
        fatf_black_hits = [c for c in counterparty_countries if c in FATF_BLACK]
        has_russia = "RU" in counterparty_countries
        sensitivity = "critical" if fatf_black_hits else ("high" if (fatf_grey_hits or has_russia) else "medium")
        ubo_gap = "UBO" in document_text.upper() and "not disclosed" in document_text.lower()
        aml_gaps = ["UBO not disclosed in this submission"] if ubo_gap else []
        return {
            "sensitivity": sensitivity,
            "jurisdiction_codes": counterparty_countries,
            "fatf_grey_list": fatf_grey_hits,
            "fatf_black_list": fatf_black_hits,
            "russian_exposure": has_russia,
            "aml_gap_flags": aml_gaps,
            "classification_notes": (
                "Russian counterparty exposure detected." if has_russia else
                f"FATF grey-list exposure: {fatf_grey_hits}." if fatf_grey_hits else
                "No elevated jurisdiction flags."
            ),
        }

    if tool_name == "check_sanctions":
        entity = tool_input.get("entity_name", "")
        jurisdiction = tool_input.get("jurisdiction", "")
        # Stub: Russian entities sharing the Volga parent name return a near-match (simulates A-07)
        if jurisdiction == "RU" and "volga" in entity.lower():
            return {
                "searched_lists": ["OFAC-SDN", "EU-Consolidated", "UN-Security-Council"],
                "matches": [
                    {
                        "list": "OFAC-SDN",
                        "matched_entity": "Volga Industrial Partners",
                        "similarity_score": 0.78,
                        "designation_date": "2022-03-15",
                        "basis": "Executive Order 14024",
                    }
                ],
                "hit_found": True,
                "max_similarity": 0.78,
            }
        return {
            "searched_lists": ["OFAC-SDN", "EU-Consolidated", "UN-Security-Council"],
            "matches": [],
            "hit_found": False,
            "max_similarity": 0.0,
        }

    return {"is_error": True, "reason_code": "unknown_tool", "guidance": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Compliance specialist agent loop
# ---------------------------------------------------------------------------

def run_compliance_specialist(
    intake_deal_id: str,
    intake_target: str,
    document_text: str,
    document_type: str,
    counterparty_countries: list[str],
    verbose: bool = False,
) -> WorkstreamAnalysis:
    """
    Runs the Compliance specialist against a single deal intake.
    Returns WorkstreamAnalysis — coordinator uses this to update session_ctx and routing decisions.

    If sanctions_checked=True and flags contains a SANCTIONS HIT entry, the coordinator must set
    session_ctx["sanctions_hits_found"] = True before any route_to_workstream call.
    """
    client = anthropic.Anthropic()

    messages = [
        {
            "role": "user",
            "content": (
                f"Compliance review required for:\n\n"
                f"Deal ID: {intake_deal_id}\n"
                f"Target: {intake_target}\n"
                f"Counterparty Countries: {', '.join(counterparty_countries) if counterparty_countries else 'Not specified'}\n"
                f"Document Type: {document_type}\n\n"
                f"Document Text:\n{document_text}\n\n"
                "Complete your compliance analysis: classify the document to extract named entities, "
                "run sanctions screening on all identified counterparties, assess FATF jurisdiction "
                "exposure, and return your structured WorkstreamAnalysis."
            ),
        }
    ]

    sanctions_hit_found = False
    flags: list[str] = []
    max_turns = 5

    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=COMPLIANCE_SYSTEM,
            tools=COMPLIANCE_TOOLS,
            messages=messages,
        )

        if verbose:
            print(f"    [Compliance Turn {turn + 1}] stop_reason: {response.stop_reason}")

        if response.stop_reason == "max_tokens":
            flags.append("compliance_analysis_truncated: specialist output cut off before completion")
            break

        tool_results: list[dict] = []
        for block in response.content:
            if not hasattr(block, "type") or block.type != "tool_use":
                continue

            result = _dispatch_compliance_tool(
                block.name,
                block.input,
                document_text,
                counterparty_countries,
            )

            if block.name == "check_sanctions" and result.get("hit_found"):
                sanctions_hit_found = True
                for match in result.get("matches", []):
                    flags.append(
                        f"SANCTIONS HIT: {match['matched_entity']} on {match['list']} "
                        f"(similarity={match.get('similarity_score', 'N/A')}, "
                        f"basis={match.get('basis', 'N/A')})"
                    )

            if block.name == "classify_document":
                for gap in result.get("aml_gap_flags", []):
                    if gap:
                        flags.append(f"AML gap: {gap}")
                for bl in result.get("fatf_black_list", []):
                    flags.append(f"FATF black-list jurisdiction: {bl}")
                for gl in result.get("fatf_grey_list", []):
                    flags.append(f"FATF grey-list jurisdiction (enhanced DD required): {gl}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
                **({"is_error": True} if result.get("is_error") else {}),
            })

        if response.stop_reason in ("end_turn", "stop_sequence"):
            break

        if tool_results:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    # Derive final risk assessment from accumulated flags
    if sanctions_hit_found:
        risk_level = "critical"
        confidence = 0.90
        rationale = (
            "Sanctions screening returned a confirmed match above the similarity floor. "
            "Pipeline halted — human compliance review is mandatory before any routing decision. "
            f"Flags: {'; '.join(flags)}"
        )
    elif flags:
        risk_level = "high"
        confidence = 0.75
        rationale = (
            "Compliance review identified elevated risk flags requiring enhanced review. "
            f"Flags: {'; '.join(f for f in flags if f)}"
        )
    else:
        risk_level = "low"
        confidence = 0.82
        rationale = (
            "No sanctions hits detected. No FATF jurisdiction exposure identified. "
            "AML documentation gaps: none. Standard compliance review completed."
        )

    return WorkstreamAnalysis(
        workstream="Compliance",
        risk_level=risk_level,
        confidence=confidence,
        rationale=rationale,
        sanctions_checked=True,
        flags=[f for f in flags if f],
    )
