"""
OrchestratorOne — Tax Specialist Agent
Handles cross-border entity structure analysis, transfer pricing risk, FATF jurisdiction flags.

Authority boundary: Tax analysis only.
Tools: classify_document (entity/jurisdiction extraction), knowledge_lookup (treaty network,
       merger control thresholds). Cannot call check_sanctions or route_to_workstream.

Usage: Spawned by coordinator after classify_intake identifies Tax as a relevant workstream.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, SPECIALIST_CONFIDENCE_FLOOR, MODEL


TAX_SYSTEM = """You are the Tax specialist in a multi-agent M&A due diligence system.

AUTHORITY: Tax analysis only. Do not advise on Legal, Financial, HR, Technology, or Compliance.

MANDATORY PROCEDURE:
1. Call classify_document to identify cross-border structures, entity types, and jurisdiction exposure.
2. Call knowledge_lookup with query_type=treaty_network for each cross-border jurisdiction pair.
3. Call knowledge_lookup with query_type=merger_control_threshold if deal value is near a filing threshold.
4. Flag transfer pricing arrangements between related entities — especially if no arms-length analysis provided.
5. Flag permanent establishment risk for entities operating in jurisdictions without treaty protection.
6. Flag withholding tax exposure on dividends and royalties in treaty-gap structures.
7. Offshore holding structures (Cayman, BVI, Bermuda) with undisclosed UBO: flag risk_level=high,
   note AML/KYC gap, but do not escalate on jurisdiction alone — Compliance handles sanctions.
8. If confidence would fall below 0.65, return inconclusive rather than guessing.

Return a structured WorkstreamAnalysis. Do not speculate on deal strategy or other workstreams."""

TAX_TOOLS = [
    {
        "name": "classify_document",
        "description": (
            "Classifies intake document to extract entity structure, jurisdiction exposure, "
            "and cross-border arrangements relevant to Tax analysis. "
            "Returns: entity_list, jurisdiction_pairs, transfer_pricing_flags, holding_structure."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {"type": "string"},
                "document_type": {"type": "string"},
            },
            "required": ["document_text", "document_type"],
        },
    },
    {
        "name": "knowledge_lookup",
        "description": (
            "Retrieves current treaty network and merger control threshold data. "
            "Use for: treaty_network (bilateral tax treaty status between two jurisdictions), "
            "merger_control_threshold (filing requirements by jurisdiction and deal value)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["treaty_network", "merger_control_threshold"],
                },
                "jurisdiction": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["query_type", "jurisdiction"],
        },
    },
]


def _dispatch_tax_tool(tool_name: str, tool_input: dict, document_text: str, countries: list[str]) -> dict:
    """Stub implementations. Replace with real treaty and regulatory API calls in production."""
    if tool_name == "classify_document":
        has_offshore = any(c in ("KY", "BM", "VG", "KN") for c in countries)
        cross_border = len(set(countries)) > 1
        return {
            "jurisdiction_codes": countries,
            "cross_border_structure": cross_border,
            "offshore_holding": has_offshore,
            "transfer_pricing_flags": ["Related party arrangement" if "related party" in document_text.lower() else None],
            "holding_structure_notes": "Offshore holding detected — UBO disclosure required" if has_offshore else "",
        }

    if tool_name == "knowledge_lookup":
        jurisdiction = tool_input.get("jurisdiction", "")
        query_type = tool_input.get("query_type")
        if query_type == "treaty_network":
            no_treaty = {"KY", "BM", "VG", "KN", "BS"}
            has_treaty = jurisdiction not in no_treaty
            return {
                "jurisdiction": jurisdiction,
                "us_treaty": has_treaty,
                "treaty_notes": "No US-jurisdiction treaty — withholding tax exposure unmitigated" if not has_treaty else "Treaty in force",
            }
        return {"jurisdiction": jurisdiction, "query_type": query_type, "result": "stub"}

    return {"is_error": True, "reason_code": "unknown_tool", "guidance": f"Unknown tool: {tool_name}"}


def run_tax_specialist(
    intake_deal_id: str,
    intake_target: str,
    document_text: str,
    document_type: str,
    counterparty_countries: list[str],
    verbose: bool = False,
) -> WorkstreamAnalysis:
    """
    Runs the Tax specialist against a single deal intake.
    Returns WorkstreamAnalysis — coordinator uses risk_level for multi-workstream trigger.
    """
    client = anthropic.Anthropic()

    messages = [
        {
            "role": "user",
            "content": (
                f"Tax review required for:\n\n"
                f"Deal ID: {intake_deal_id}\n"
                f"Target: {intake_target}\n"
                f"Counterparty Countries: {', '.join(counterparty_countries) if counterparty_countries else 'Not specified'}\n"
                f"Document Type: {document_type}\n\n"
                f"Document Text:\n{document_text}\n\n"
                "Complete your Tax analysis: classify the document to identify cross-border structures, "
                "check treaty network for each jurisdiction pair, flag transfer pricing and PE risks, "
                "and return your structured WorkstreamAnalysis."
            ),
        }
    ]

    flags: list[str] = []
    max_turns = 5

    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=TAX_SYSTEM,
            tools=TAX_TOOLS,
            messages=messages,
        )

        if verbose:
            print(f"    [Tax Turn {turn + 1}] stop_reason: {response.stop_reason}")

        if response.stop_reason == "max_tokens":
            flags.append("tax_analysis_truncated: specialist output cut off before completion")
            break

        tool_results: list[dict] = []
        for block in response.content:
            if not hasattr(block, "type") or block.type != "tool_use":
                continue

            result = _dispatch_tax_tool(block.name, block.input, document_text, counterparty_countries)

            if block.name == "classify_document":
                if result.get("offshore_holding"):
                    flags.append(f"Offshore holding structure detected: {result.get('holding_structure_notes', '')}")
                for tp in result.get("transfer_pricing_flags", []):
                    if tp:
                        flags.append(f"Transfer pricing: {tp}")

            if block.name == "knowledge_lookup" and result.get("us_treaty") is False:
                flags.append(f"No treaty: {result.get('treaty_notes', '')}")

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

    if flags:
        risk_level = "high"
        confidence = 0.78
        rationale = f"Tax review identified {len(flags)} flag(s) requiring specialist attention. Flags: {'; '.join(f for f in flags if f)}"
    else:
        risk_level = "low"
        confidence = 0.85
        rationale = "No material Tax flags identified. Cross-border structure reviewed; treaty network confirmed."

    return WorkstreamAnalysis(
        workstream="Tax",
        risk_level=risk_level,
        confidence=confidence,
        rationale=rationale,
        sanctions_checked=False,
        flags=[f for f in flags if f],
    )
