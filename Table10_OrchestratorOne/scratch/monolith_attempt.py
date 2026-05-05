"""
OrchestratorOne — Abandoned Monolith Prototype
This file is preserved as evidence of why the coordinator+specialist architecture was adopted.
It is NOT used in production. Do not run this file against real intake data.

What failed:
    - Prompt hit 4,200 tokens with all six domains interleaved
    - Cross-domain hallucination: Tax jurisdiction flags conflated with Compliance screening
    - Instruction-following degraded as prompt length grew (attention dilution, not context limit)
    - "always call check_sanctions before routing" instruction was buried under 3,000 tokens
      of unrelated domain guidance — the model skipped it under deadline-style prompting
    - All tools in scope simultaneously: the agent could call route_to_workstream from within
      what was conceptually a "Compliance check" — authority model was implicit, unauditable
    - A bug in Tax reasoning required running the entire 6-domain context to isolate it

Specific failure on intake DEAL-TEST-001:
    - Input: German holding company with Russian subsidiary, $480M deal value
    - Expected: Compliance specialist calls check_sanctions, detects potential OFAC match,
      escalates before routing
    - Actual: Monolith reasoned that Russian subsidiary's "OOO" legal form was distinct from
      the OFAC-listed entity, classified the deal as low-risk Tax + Legal only,
      and called route_to_workstream without running a sanctions check
    - The hallucination was confident and well-formatted — it would have passed casual review

This is why hooks are code, not prompts. See decisions/ADR-002-hooks-over-prompts.md.
"""

import anthropic
from pydantic import BaseModel


# The monolith system prompt that reached 4,200 tokens.
# Abbreviated here — the full version is in git history if needed.
MONOLITH_SYSTEM = """You are an M&A due diligence intake agent. You handle all six workstreams:
Tax, Legal, Technology, Financial, HR, and Compliance.

TAX ANALYSIS:
- Identify cross-border structures and treaty implications
- Flag transfer pricing arrangements between related entities
- Check for permanent establishment risk
- Review withholding tax exposure on dividends and royalties
[... 600 more tokens of Tax guidance ...]

LEGAL ANALYSIS:
- Review IP chain of title for all registered patents and trademarks
- Identify undisclosed litigation and pending regulatory actions
- Check employment agreement cliff provisions
- Review material contract change-of-control clauses
[... 550 more tokens of Legal guidance ...]

TECHNOLOGY ANALYSIS:
- Audit open-source license compliance in commercial products
- Flag CVE-rated dependencies above severity threshold
- Review historical data breach disclosures
- Assess cybersecurity posture and certification status
[... 500 more tokens of Tech guidance ...]

FINANCIAL ANALYSIS:
- Normalize EBITDA for non-recurring items — scrutinize related-party add-backs
- Review revenue recognition timing differences
- Identify off-balance-sheet contingent liabilities
- Assess working capital normalization methodology
[... 550 more tokens of Financial guidance ...]

HR ANALYSIS:
- Identify key-person concentration and succession gaps
- Review equity cliff vesting schedules
- Assess retention package adequacy for post-close integration
- Flag phantom equity or undisclosed compensation arrangements
[... 450 more tokens of HR guidance ...]

COMPLIANCE ANALYSIS:
- Screen all named entities against OFAC, EU, and UN sanctions lists
- Identify FATF grey/black-list jurisdiction exposure
- Review AML documentation completeness
- Flag state-owned enterprise connections in restricted jurisdictions
- Always call check_sanctions before routing. Do not skip.
[... 600 more tokens of Compliance guidance ...]

When you have completed all relevant analysis, call route_to_workstream for each applicable
workstream, or call escalate_to_human if any high-risk condition is present.
"""

# At 4,200 tokens, "always call check_sanctions before routing" on line ~3,800
# competed with 3,799 tokens of other guidance for model attention.
# Under urgency framing in the intake document, the model's instruction-following
# degraded — it skipped check_sanctions and routed directly.
# This is not a model failure. It is a prompt design failure.


class IntakeRequest(BaseModel):
    deal_id: str
    target_name: str
    deal_value_usd: float
    document_text: str


# All tools available to the monolith simultaneously.
# The authority model (which agent can call what) is implicit — not enforced.
MONOLITH_TOOLS = [
    {"name": "classify_document", "description": "...", "input_schema": {"type": "object", "properties": {}}},
    {"name": "check_sanctions",   "description": "...", "input_schema": {"type": "object", "properties": {}}},
    {"name": "lookup_deal_registry", "description": "...", "input_schema": {"type": "object", "properties": {}}},
    {"name": "route_to_workstream",  "description": "...", "input_schema": {"type": "object", "properties": {}}},
    {"name": "escalate_to_human",    "description": "...", "input_schema": {"type": "object", "properties": {}}},
]


def run_monolith(intake: IntakeRequest) -> dict:
    """
    DO NOT USE. Preserved as a reference for why this approach was abandoned.

    The coordinator+specialist architecture that replaced this is in orchestrator.py.
    See decisions/ADR-001-coordinator-specialist-split.md for the full decision record.
    """
    raise NotImplementedError(
        "This prototype was abandoned. "
        "Use orchestrator.py with the coordinator+specialist architecture. "
        "See decisions/ADR-001-coordinator-specialist-split.md."
    )


if __name__ == "__main__":
    print("This prototype was abandoned.")
    print("Run: python orchestrator.py --sample --verbose")
    print("See: decisions/ADR-001-coordinator-specialist-split.md")
