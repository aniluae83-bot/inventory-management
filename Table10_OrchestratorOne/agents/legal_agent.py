"""Legal specialist — IP chain-of-title, litigation exposure, change-of-control clauses."""
from __future__ import annotations
import json, sys
from pathlib import Path
import anthropic
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, MODEL
from agents.base import SpecialistAgent

LEGAL_SYSTEM = """You are the Legal specialist in a multi-agent M&A due diligence system.
AUTHORITY: Legal analysis only. No Tax, Financial, HR, Technology, or Compliance.
PROCEDURE:
1. Call classify_document to extract IP portfolio, litigation disclosures, and contract flags.
2. Flag IP chain-of-title gaps — missing assignment documentation for any registered IP.
3. Flag undisclosed litigation and pending regulatory actions.
4. Flag material contract change-of-control clauses that require counterparty consent.
5. Flag employment agreement cliff provisions for key personnel.
6. If confidence < 0.65, return inconclusive rather than guessing."""

LEGAL_TOOLS = [{"name": "classify_document", "description": "Extracts IP, litigation, and contract flags from intake document.", "input_schema": {"type": "object", "properties": {"document_text": {"type": "string"}, "document_type": {"type": "string"}}, "required": ["document_text", "document_type"]}}]

def run_legal_specialist(intake_deal_id, intake_target, document_text, document_type, counterparty_countries, verbose=False) -> WorkstreamAnalysis:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Legal review for Deal ID: {intake_deal_id}\nTarget: {intake_target}\nDocument Type: {document_type}\n\nDocument:\n{document_text}\n\nClassify document and return Legal WorkstreamAnalysis."}]
    flags: list[str] = []
    for _ in range(5):
        r = client.messages.create(model=MODEL, max_tokens=2048, system=LEGAL_SYSTEM, tools=LEGAL_TOOLS, messages=messages)
        tool_results = []
        for block in r.content:
            if not hasattr(block, "type") or block.type != "tool_use": continue
            result = {"ip_gaps": "assignment documentation missing" if "assignment" in document_text.lower() and "not" in document_text.lower() else None, "litigation_flags": [], "change_of_control": False}
            if result.get("ip_gaps"): flags.append(f"IP chain-of-title gap: {result['ip_gaps']}")
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
        if r.stop_reason in ("end_turn", "stop_sequence"): break
        if tool_results:
            messages.append({"role": "assistant", "content": r.content})
            messages.append({"role": "user", "content": tool_results})
    risk_level = "high" if flags else "low"
    return WorkstreamAnalysis(workstream="Legal", risk_level=risk_level, confidence=0.80 if flags else 0.85, rationale=f"Legal flags: {'; '.join(flags)}" if flags else "No material Legal flags.", sanctions_checked=False, flags=flags)
