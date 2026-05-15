import json
import os
from typing import Optional

from core.state.manifest import TaskManifest, PipelineStatus
from util import getClient


def run(manifest: TaskManifest, review_feedback: Optional[str] = None) -> TaskManifest:
    local_path = manifest.repo_local_path
    client = getClient()

    spec_content = _read_file(local_path, "SPEC.md")
    agent_instructions = _read_file(local_path, "DEV_AGENT.md")

    feedback_section = (
        f"\nReview feedback to address:\n{review_feedback}\n"
        if review_feedback else ""
    )

    messages = [
        ("system", agent_instructions),
        ("user", f"""Implement every task defined in the spec below. Do NOT include test files.
{feedback_section}
Spec:
{spec_content}

Return a JSON object where keys are file paths relative to the repo root and values are complete file contents.
Return ONLY valid JSON, no markdown fences."""),
    ]

    response = client.invoke(messages)
    files = json.loads(response.text)
    manifest.generated_code = files

    for filepath, content in files.items():
        full = os.path.join(local_path, filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    print(f"✅ Dev agent wrote {len(files)} file(s)")
    manifest.status = PipelineStatus.REVIEWING
    return manifest


def _read_file(base: str, filename: str) -> str:
    path = os.path.join(base, filename)
    if not os.path.exists(path):
        return f"(No {filename} found)"
    with open(path) as f:
        return f.read()
