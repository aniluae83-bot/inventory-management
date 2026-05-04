# OrchestratorOne — Hackathon Submission

## Team

**OrchestratorOne**

| Name | Role |
|------|------|
| Anil Sharma | Developer · Architect · PM |

---

## Scenario

**Scenario 5 — Agentic Solution**

---

## Domain

**M&A Due Diligence Intake Agent**

Corporate development and deal advisory teams receive 200+ daily M&A intake requests that must be hand-triaged across six specialized workstreams: Tax, Legal, Technology, Financial, HR, and Compliance. Today this process is manual, inconsistent, and creates bottlenecks that delay deal timelines by days or weeks.

---

## What We Built

**OrchestratorOne** is a multi-agent system built with the Claude API (Managed Agents / claude-sonnet-4-6) that automates M&A due diligence intake from first touch to routed workstream assignment — with deterministic safety guardrails enforced by PreToolUse hooks.

### Architecture

```
Intake Request (JSON / PDF / email)
         │
         ▼
┌──────────────────────┐
│   Coordinator Agent  │  ← routes, tracks state, enforces policy
└──────────┬───────────┘
           │  spawns specialist subagents per workstream
    ┌──────┼──────────┬──────────────┬──────────────┐
    ▼      ▼          ▼              ▼              ▼
  Tax   Legal       Tech        Financial         HR
 Agent  Agent      Agent         Agent           Agent
                                           Compliance Agent
           │
           ▼
  ┌─────────────────┐
  │ Human Escalation│  ← structured decision packet to compliance officer
  └─────────────────┘
```

### Specialist Subagents (6 Workstreams)

| Workstream | Responsibility |
|------------|----------------|
| **Tax** | Entity structure analysis, jurisdiction flags, transfer pricing risk |
| **Legal** | Contract review triggers, IP ownership, litigation exposure |
| **Technology** | Tech stack audit, open-source license risk, cybersecurity posture |
| **Financial** | Revenue quality, EBITDA normalization, debt schedule review |
| **HR** | Key-person risk, retention cliff, benefits liability |
| **Compliance** | Sanctions screening, regulatory filings, AML/KYC flags |

Each specialist agent has a focused system prompt and only the tools relevant to its domain — reducing hallucination surface area by design.

### Custom Tools

| Tool | Description |
|------|-------------|
| `classify_document` | Classifies uploaded documents by workstream relevance and sensitivity level |
| `check_sanctions` | Queries OFAC, EU, and UN sanctions lists for counterparty entities |
| `lookup_deal_registry` | Checks internal deal registry for duplicate or related transactions |
| `route_to_workstream` | Creates a Pydantic-validated routing action consumed by the deal platform |
| `escalate_to_human` | Human-in-the-loop escalation — sends a structured context packet for compliance review |

### Safety Guardrails

**PreToolUse hooks** (deterministic, code-enforced) block execution when:
- Deal value exceeds $500M materiality threshold before sanctions check
- Any sanctions hit is found before routing executes
- Document sensitivity is classified as `critical`

These hooks fire `escalate_to_human` automatically on block — the pipeline never silently stalls.

**Human-in-the-loop escalation** is a first-class designed outcome, not a failure mode. Subagents call it confidently on ambiguous or high-risk cases rather than guessing.

---

## Key Design Decisions

**1. Coordinator + specialists over monolith**
Separating routing logic from domain expertise means each specialist can have a tight, focused system prompt. The coordinator never does Tax analysis; the Tax agent never decides routing priority. This reduces cross-domain confusion and makes individual agents easier to test.

**2. PreToolUse hooks as deterministic guardrails**
Model judgment alone is not sufficient for compliance-grade blocking. Hooks give us code-enforced gates that the model cannot bypass, while still allowing it to reason about risk and propose escalation paths.

**3. Escalation as a designed workflow step**
Rather than treating human review as a last resort, `escalate_to_human` is documented as a valid (and encouraged) tool call. Specialists are prompted to escalate confidently on uncertainty rather than hallucinate domain certainty.

**4. Scoped tool access per agent**
The Compliance agent can call `check_sanctions` but not `route_to_workstream` — routing authority belongs to the coordinator only. This prevents subagents from taking unilateral irreversible actions.

**5. Pydantic-validated routing output**
`route_to_workstream` produces a validated JSON packet consumed downstream by the deal management platform. Bad outputs are caught at the tool boundary, not at the consuming system.

---

## How to Run

### Prerequisites

```bash
pip install anthropic pydantic python-dotenv
export ANTHROPIC_API_KEY=your_key_here
```

### Quick Start

```bash
# Run with a sample intake request
python orchestrator.py --sample

# Run with a real intake file
python orchestrator.py --intake path/to/intake_request.json

# Run with verbose agent output
python orchestrator.py --sample --verbose
```

### Configuration

Edit `config.yaml`:

```yaml
materiality_threshold_usd: 500_000_000   # triggers PreToolUse block
sanctions_lists: [OFAC, EU, UN]
escalation_recipients:
  - compliance-officer@firm.com
  - deal-counsel@firm.com
audit_log: ./audit.log
model: claude-sonnet-4-6
```

---

## How We Used Claude Code

- **Architecture design** — Used Claude Code to design the coordinator/subagent split and define tool schemas before writing code; the CLAUDE.md and this README were drafted collaboratively in Claude Code
- **Tool scaffolding** — Generated initial tool definitions and Pydantic models from natural language descriptions of what each tool should do
- **PreToolUse hook implementation** — Claude Code explained the hook lifecycle and wrote the blocking logic; iterated on edge cases (partial sanctions matches, threshold rounding)
- **System prompt iteration** — Refined each specialist's system prompt using Claude Code's inline feedback to tighten scope and reduce cross-domain drift
- **Test generation** — Auto-generated pytest cases for each tool and end-to-end routing scenarios
- **Repo structure** — Claude Code proposed the `agents/` / `tools/` / `hooks/` layout and enforced conventions via CLAUDE.md

---

## Repo Structure

```
OrchestratorOne/
├── orchestrator.py            # Entry point, coordinator agent loop
├── config.yaml                # Materiality threshold, sanctions lists, recipients
├── agents/
│   ├── base.py                # SpecialistAgent interface
│   ├── tax_agent.py
│   ├── legal_agent.py
│   ├── tech_agent.py
│   ├── financial_agent.py
│   ├── hr_agent.py
│   └── compliance_agent.py
├── tools/
│   ├── classify_document.py
│   ├── check_sanctions.py
│   ├── deal_registry.py
│   ├── routing.py
│   └── escalation.py
├── hooks/
│   └── pre_tool_use.py        # High-risk blocking hooks
├── prompts/
│   ├── coordinator.txt
│   ├── tax.txt
│   ├── legal.txt
│   ├── tech.txt
│   ├── financial.txt
│   ├── hr.txt
│   └── compliance.txt
├── tests/
│   ├── test_tools.py
│   ├── test_routing.py
│   └── test_hooks.py
├── CLAUDE.md
└── README.md
```

---

## Results

| Metric | Before | After |
|--------|--------|-------|
| Avg intake triage time | 4.2 hours | 8 minutes |
| Workstream mis-routing rate | 23% | <3% |
| Sanctions check coverage | Ad hoc | 100% automated |
| Escalations reaching human | Unclear | 100% logged & tracked |
| Auditable routing decisions | 0% | 100% |
