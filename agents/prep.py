import json
import re
from typing import Optional

from agents.codebase_intel import query_context
from checkpoints.db import create_table, save_checkpoint
from core.state.manifest import TaskManifest, PipelineStatus
from util import getClient


def run(manifest: TaskManifest, feedback: Optional[str] = None) -> TaskManifest:
    context = query_context(manifest.story_text)
    client = getClient()

    feedback_section = (
        f"\nThe previous spec was rejected with the following feedback:\n{feedback}\nPlease revise the spec accordingly.\n"
        if feedback else ""
    )

    messages = [
        ("system", "You are a Tech Lead who knows about the project's codebase and architecture."),
        ("user", f"""
Story: {manifest.story_text}
Acceptance Criteria:
{chr(10).join(manifest.acceptance_criteria)}

Existing codebase context:
{context}
{feedback_section}
Produce a technical spec with clearly numbered tasks that includes:
1. Files to create or modify (with paths)
2. Function signatures needed
3. Data structures
4. How each acceptance criterion is satisfied

Also decide which agents are needed from this list: ["test", "dev", "review"].
For most stories all three are needed. Only omit one if the story explicitly doesn't require it.

Return your response as JSON with two keys:
{{
  "spec": "<full spec text in markdown>",
  "selected_agents": ["test", "dev", "review"]
}}

Return ONLY valid JSON, no markdown fences.
""")
    ]

    response = client.invoke(messages)

    # Parse JSON response
    try:
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        parsed = json.loads(json_str)
        manifest.spec_doc = parsed["spec"]
        manifest.selected_agents = parsed.get("selected_agents", ["test", "dev", "review"])
    except Exception:
        # Fallback: treat entire response as spec
        manifest.spec_doc = response.text
        manifest.selected_agents = ["test", "dev", "review"]

    manifest.status = PipelineStatus.AWAITING_SPEC_APPROVAL

    create_table()
    save_checkpoint(manifest)

    return manifest


if __name__ == "__main__":
    print("Testing prep agent...")
    manifest = TaskManifest(jira_id="TT-1", status=PipelineStatus.INITIATED)
    updated_manifest = run(manifest)
    print(f"Selected agents: {updated_manifest.selected_agents}")
    print(updated_manifest.spec_doc)
