# agents/remediation/agent.py
import anthropic
from core.state.manifest import TaskManifest, PipelineStatus

client = anthropic.Anthropic()
MAX_RETRIES = 2

def run(manifest: TaskManifest) -> TaskManifest:
    if manifest.retry_count >= MAX_RETRIES:
        manifest.status = PipelineStatus.ESCALATED
        manifest.failure_reason = "Max retries exceeded. Human intervention needed."
        return manifest

    issues = "\n".join(manifest.review_result.issues)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Review failed with these issues:
{issues}

Classify where to route:
- "dev" if code logic needs fixing
- "prep" if the spec is ambiguous or wrong
- "escalate" if the problem is systemic

Return only one word: dev, prep, or escalate."""
        }]
    )

    decision = response.content[0].text.strip().lower()
    manifest.retry_count += 1

    if decision == "prep":
        manifest.status = PipelineStatus.PREPPING
    elif decision == "escalate":
        manifest.status = PipelineStatus.ESCALATED
    else:
        manifest.status = PipelineStatus.DEVELOPING

    return manifest