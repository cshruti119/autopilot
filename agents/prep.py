from typing import Optional

from agents.codebase_intel import query_context
from checkpoints.db import create_table, save_checkpoint
from core.state.manifest import TaskManifest, PipelineStatus
from util import getClient


def run(manifest: TaskManifest, feedback: Optional[str] = None) -> TaskManifest:
    context = query_context(manifest.story_text)
    client = getClient()

    feedback_section = ""
    if feedback:
        feedback_section = f"\nThe previous spec was rejected with the following feedback:\n{feedback}\nPlease revise the spec accordingly.\n"

    messages = [
        ("system", "You are a Tech Lead who knows about the project's codebase and architecture."),
        ("user", f"""
Story: {manifest.story_text}
Acceptance Criteria:
{chr(10).join(manifest.acceptance_criteria)}

Existing codebase context:
{context}
{feedback_section}
Produce a spec with:
1. Files to create or modify (with paths)
2. Function signatures needed
3. Data structures
4. How each acceptance criterion is satisfied

Be precise. No code yet, just the spec.
""")
    ]

    response = client.invoke(messages)

    manifest.spec_doc = response.text
    manifest.status = PipelineStatus.AWAITING_SPEC_APPROVAL

    create_table()
    save_checkpoint(manifest)

    return manifest


if __name__ == "__main__":
    print("Testing prep agent...")
    manifest = TaskManifest(
        jira_id="TT-1",
        status=PipelineStatus.INITIATED,
    )
    updated_manifest = run(manifest)
    print(updated_manifest.spec_doc)
