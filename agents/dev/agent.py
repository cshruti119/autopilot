# agents/dev/agent.py
import anthropic, subprocess, os
from core.state.manifest import TaskManifest, PipelineStatus

client = anthropic.Anthropic()

def run(manifest: TaskManifest) -> TaskManifest:
    repo_path = os.getenv("TARGET_REPO_PATH")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": f"""You are a Developer. Implement code based on this spec.

Spec:
{manifest.spec_doc}

Return a JSON object where keys are relative file paths and values are 
complete file contents. Return ONLY valid JSON, no markdown."""
        }]
    )

    import json
    files = json.loads(response.content[0].text)
    manifest.generated_code = files

    # Write files to sandbox (NOT directly to repo)
    sandbox = f"/tmp/aifsd_sandbox_{manifest.jira_id}"
    os.makedirs(sandbox, exist_ok=True)
    for filepath, content in files.items():
        full = os.path.join(sandbox, filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    manifest.status = PipelineStatus.RECONCILING
    return manifest