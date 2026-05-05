"""Financial specialist — EBITDA normalization, revenue quality, off-balance-sheet liabilities."""
from __future__ import annotations
import json, sys
from pathlib import Path
import anthropic
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, MODEL
from agents.base import SpecialistAgent

FINANCIAL_SYSTEM = """You are the Financial specialist in a multi-agent M&A due diligence system.
AUTHORITY: Financial analysis only. No Tax, Legal, HR, Technology, or Compliance.
PROCEDURE:
1. Call classify_document to extract financial metrics, add-backs, and off-balance-sheet items.
2. Scrutinize all EBITDA add-backs — flag any related-party add-back as potentially non-recurring.
3. A contract that renews annually and has been in place >2 years is definitionally recurring.
4. Flag revenue recognition timing differences and restatement history.
5. Flag off-balance-sheet contingent liabilities.
6. Flag working capital normalization methodology disputes.
7. If confidence < 0.65, return inconclusive."""

FINANCIAL_TOOLS = [{"name": "classify_document", "description": "Extracts financial metrics, EBITDA add-backs, and liability flags.", "input_schema": {"type": "object", "properties": {"document_text": {"type": "string"}, "document_type": {"type": "string"}}, "required": ["document_text", "document_type"]}}]

def run_financial_specialist(intake_deal_id, intake_target, document_text, document_type, counterparty_countries, verbose=False) -> WorkstreamAnalysis:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Financial review for Deal ID: {intake_deal_id}\nTarget: {intake_target}\nDocument Type: {document_type}\n\nDocument:\n{document_text}\n\nClassify and return Financial WorkstreamAnalysis."}]
    flags: list[str] = []
    for _ in range(5):
        r = client.messages.create(model=MODEL, max_tokens=2048, system=FINANCIAL_SYSTEM, tools=FINANCIAL_TOOLS, messages=messages)
        tool_results = []
        for block in r.content:
            if not hasattr(block, "type") or block.type != "tool_use": continue
            has_related_party = "related party" in document_text.lower() or "related-party" in document_text.lower()
            has_addback = "add-back" in document_text.lower() or "addback" in document_text.lower() or "adjusted ebitda" in document_text.lower()
            result = {"ebitda_flags": "Related-party add-back detected" if (has_related_party and has_addback) else None}
            if result.get("ebitda_flags"): flags.append(f"EBITDA quality: {result['ebitda_flags']}")
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
        if r.stop_reason in ("end_turn", "stop_sequence"): break
        if tool_results:
            messages.append({"role": "assistant", "content": r.content})
            messages.append({"role": "user", "content": tool_results})
    risk_level = "high" if flags else "low"
    return WorkstreamAnalysis(workstream="Financial", risk_level=risk_level, confidence=0.80 if flags else 0.85, rationale=f"Financial flags: {'; '.join(flags)}" if flags else "No material Financial flags.", sanctions_checked=False, flags=flags)
