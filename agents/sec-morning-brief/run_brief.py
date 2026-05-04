import os
import time
from datetime import date
import anthropic

AGENT_ID = os.environ["SEC_BRIEF_AGENT_ID"]
ENV_ID = os.environ["SEC_BRIEF_ENV_ID"]

client = anthropic.Anthropic()


def run_brief():
    today = date.today().isoformat()

    session = client.beta.sessions.create(
        agent=AGENT_ID,
        environment_id=ENV_ID,
        title=f"SEC Morning Brief {today}",
    )
    print(f"Session {session.id} started")

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

    # Brief indexing lag before output files appear
    time.sleep(3)

    files = client.beta.files.list(
        scope_id=session.id,
        betas=["managed-agents-2026-04-01"],
    )

    for f in files.data:
        output_path = f"sec_brief_{today}.md"
        client.beta.files.download(f.id).write_to_file(output_path)
        print(f"\nBrief saved to {output_path}")

    client.beta.sessions.archive(session_id=session.id)


if __name__ == "__main__":
    run_brief()
