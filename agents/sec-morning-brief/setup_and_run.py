"""
First run: creates the agent + environment, saves IDs to .env, then runs the brief.
Subsequent runs: loads IDs from .env (or env vars) and runs the brief directly.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
    python agents/sec-morning-brief/setup_and_run.py
"""

import os
import time
from datetime import date
from pathlib import Path
import anthropic

HERE = Path(__file__).parent
ENV_FILE = HERE / ".env"

SYSTEM_PROMPT = """\
You are a financial regulatory intelligence agent. Each morning:

1. Search SEC EDGAR (https://efts.sec.gov/LATEST/search-index?q=&dateRange=custom&startdt=YESTERDAY&enddt=TODAY) and https://www.sec.gov/cgi-bin/browse-edgar for filings and regulatory updates from the past 24 hours.
2. Search for overnight news on SEC regulations, financial compliance, and market-moving regulatory developments.
3. Score each item 1-10 on: breadth of market impact, recency, actionability for compliance teams, and public attention.
4. Write the brief to /mnt/session/outputs/sec_brief_YYYY-MM-DD.md using today's actual date.

Brief structure (target ~500 words, one printed page):
# SEC Morning Brief - [Date]
## Executive Summary
2-3 sentences covering the day's regulatory landscape.
## Top 5 Items
Numbered, sorted by relevance score descending. Each item: what happened, why it matters, relevance score X/10.\
"""

client = anthropic.Anthropic()


def load_ids():
    """Load agent/env IDs from env vars or .env file."""
    agent_id = os.environ.get("SEC_BRIEF_AGENT_ID")
    env_id = os.environ.get("SEC_BRIEF_ENV_ID")

    if not agent_id or not env_id:
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if line.startswith("SEC_BRIEF_AGENT_ID="):
                    agent_id = line.split("=", 1)[1].strip()
                elif line.startswith("SEC_BRIEF_ENV_ID="):
                    env_id = line.split("=", 1)[1].strip()

    return agent_id, env_id


def setup():
    """Create agent and environment once; persist IDs to .env."""
    print("Creating environment...")
    environment = client.beta.environments.create(
        name="sec-morning-brief-env",
        description="Unrestricted network access for SEC EDGAR and news sources",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"  Environment: {environment.id}")

    print("Creating agent...")
    agent = client.beta.agents.create(
        name="SEC Morning Brief Agent",
        model="claude-opus-4-7",
        system=SYSTEM_PROMPT,
        tools=[{"type": "agent_toolset_20260401"}],
    )
    print(f"  Agent: {agent.id}")

    ENV_FILE.write_text(
        f"SEC_BRIEF_AGENT_ID={agent.id}\n"
        f"SEC_BRIEF_ENV_ID={environment.id}\n"
    )
    print(f"IDs saved to {ENV_FILE}\n")
    print("Add these to GitHub secrets for the scheduled workflow:")
    print(f"  SEC_BRIEF_AGENT_ID={agent.id}")
    print(f"  SEC_BRIEF_ENV_ID={environment.id}\n")

    return agent.id, environment.id


def run_brief(agent_id, env_id):
    today = date.today().isoformat()

    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"SEC Morning Brief {today}",
    )
    print(f"Session {session.id} started\n{'-' * 60}")

    # Stream-first, then send
    with client.beta.sessions.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{
                "type": "user.message",
                "content": [{"type": "text", "text": f"Generate today's SEC Morning Brief for {today}."}],
            }],
        )

        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(block.text, end="", flush=True)
            elif event.type == "session.status_terminated":
                break
            elif event.type == "session.status_idle":
                if event.stop_reason.type != "requires_action":
                    break

    print(f"\n{'-' * 60}")

    # Brief indexing lag before output files appear
    time.sleep(3)

    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )

    if not files.data:
        print("No output files found in session outputs.")
    for f in files.data:
        output_path = HERE / f"sec_brief_{today}.md"
        client.beta.files.download(f.id).write_to_file(str(output_path))
        print(f"Brief saved to {output_path}")

    client.beta.sessions.archive(session_id=session.id)


if __name__ == "__main__":
    agent_id, env_id = load_ids()

    if not agent_id or not env_id:
        agent_id, env_id = setup()
    else:
        print(f"Using agent {agent_id} / environment {env_id}\n")

    run_brief(agent_id, env_id)
