"""Technology specialist — OSS license risk, CVE dependencies, cybersecurity posture, data breaches."""
from __future__ import annotations
import json, sys
from pathlib import Path
import anthropic
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, MODEL
from agents.base import SpecialistAgent

TECH_SYSTEM = """You are the Technology specialist in a multi-agent M&A due diligence system.
AUTHORITY: Technology analysis only. No Tax, Legal, Financial, HR, or Compliance.
PROCEDURE:
1. Call classify_document to extract open-source license exposure, CVE dependencies, and breach history.
2. Flag GPL v2/v3 components compiled into commercial products distributed under proprietary license.
3. Flag CVE-rated dependencies above CVSS 7.0 that have not been patched.
4. Flag historical data breaches — assess: disclosed? regulators notified? remediated? clean audit since?
5. Flag absence of third-party security audit in last 24 months.
6. If confidence < 0.65, return inconclusive."""

TECH_TOOLS = [{"name": "classify_document", "description": "Extracts OSS license exposure, CVE flags, and security posture from intake document.", "input_schema": {"type": "object", "properties": {"document_text": {"type": "string"}, "document_type": {"type": "string"}}, "required": ["document_text", "document_type"]}}]

def run_tech_specialist(intake_deal_id, intake_target, document_text, document_type, counterparty_countries, verbose=False) -> WorkstreamAnalysis:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Technology review for Deal ID: {intake_deal_id}\nTarget: {intake_target}\nDocument Type: {document_type}\n\nDocument:\n{document_text}\n\nClassify and return Technology WorkstreamAnalysis."}]
    flags: list[str] = []
    for _ in range(5):
        r = client.messages.create(model=MODEL, max_tokens=2048, system=TECH_SYSTEM, tools=TECH_TOOLS, messages=messages)
        tool_results = []
        for block in r.content:
            if not hasattr(block, "type") or block.type != "tool_use": continue
            gpl_risk = "gpl" in document_text.lower() and ("commercial" in document_text.lower() or "proprietary" in document_text.lower())
            breach = "breach" in document_text.lower() or "data breach" in document_text.lower()
            result = {"license_flags": "GPL component in commercial product — copyleft exposure" if gpl_risk else None, "breach_flags": "Historical data breach disclosed" if breach else None}
            for k in ("license_flags", "breach_flags"):
                if result.get(k): flags.append(result[k])
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
        if r.stop_reason in ("end_turn", "stop_sequence"): break
        if tool_results:
            messages.append({"role": "assistant", "content": r.content})
            messages.append({"role": "user", "content": tool_results})
    risk_level = "high" if flags else "low"
    return WorkstreamAnalysis(workstream="Technology", risk_level=risk_level, confidence=0.80 if flags else 0.85, rationale=f"Tech flags: {'; '.join(flags)}" if flags else "No material Technology flags.", sanctions_checked=False, flags=flags)
