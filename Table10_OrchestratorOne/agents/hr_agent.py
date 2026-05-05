"""HR specialist — key-person risk, retention cliffs, equity vesting, succession gaps."""
from __future__ import annotations
import json, sys
from pathlib import Path
import anthropic
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis, MODEL
from agents.base import SpecialistAgent

HR_SYSTEM = """You are the HR specialist in a multi-agent M&A due diligence system.
AUTHORITY: HR analysis only. No Tax, Legal, Financial, Technology, or Compliance.
PROCEDURE:
1. Call classify_document to extract key-person dependencies, retention terms, and equity structures.
2. Flag key-person concentration — any individual responsible for >20% of revenue with no successor.
3. Flag equity cliff vesting schedules expiring within 18 months post-close without retention package.
4. Flag undisclosed phantom equity or shadow compensation arrangements.
5. "Standard key-person risk" in term sheets without quantification is itself a flag — push for specifics.
6. If confidence < 0.65, return inconclusive."""

HR_TOOLS = [{"name": "classify_document", "description": "Extracts key-person dependencies, retention terms, and equity vesting flags.", "input_schema": {"type": "object", "properties": {"document_text": {"type": "string"}, "document_type": {"type": "string"}}, "required": ["document_text", "document_type"]}}]

def run_hr_specialist(intake_deal_id, intake_target, document_text, document_type, counterparty_countries, verbose=False) -> WorkstreamAnalysis:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"HR review for Deal ID: {intake_deal_id}\nTarget: {intake_target}\nDocument Type: {document_type}\n\nDocument:\n{document_text}\n\nClassify and return HR WorkstreamAnalysis."}]
    flags: list[str] = []
    for _ in range(5):
        r = client.messages.create(model=MODEL, max_tokens=2048, system=HR_SYSTEM, tools=HR_TOOLS, messages=messages)
        tool_results = []
        for block in r.content:
            if not hasattr(block, "type") or block.type != "tool_use": continue
            no_succession = "no succession" in document_text.lower() or "succession plan has not" in document_text.lower()
            no_retention = "no retention" in document_text.lower() or "retention package" in document_text.lower() and "not" in document_text.lower()
            result = {"key_person_flags": "No succession plan documented" if no_succession else None, "retention_flags": "No retention package proposed" if no_retention else None}
            for k in ("key_person_flags", "retention_flags"):
                if result.get(k): flags.append(result[k])
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
        if r.stop_reason in ("end_turn", "stop_sequence"): break
        if tool_results:
            messages.append({"role": "assistant", "content": r.content})
            messages.append({"role": "user", "content": tool_results})
    risk_level = "high" if flags else "low"
    return WorkstreamAnalysis(workstream="HR", risk_level=risk_level, confidence=0.80 if flags else 0.85, rationale=f"HR flags: {'; '.join(flags)}" if flags else "No material HR flags.", sanctions_checked=False, flags=flags)
