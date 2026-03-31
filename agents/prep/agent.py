# agents/prep/agent.py
import anthropic
from agents.codebase_intel.agent import query_context
from core.state.manifest import TaskManifest, PipelineStatus

client = anthropic.Anthropic()

def run(manifest: TaskManifest) -> TaskManifest:
    context = query_context(manifest.story_text)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""You are a Tech Lead. Write an implementation spec.
            
Story: {manifest.story_text}

Acceptance Criteria:
{chr(10).join(manifest.acceptance_criteria)}

Existing codebase context:
{context}

Produce a spec with:
1. Files to create or modify (with paths)
2. Function signatures needed
3. Data structures
4. How each acceptance criterion is satisfied

Be precise. No code yet, just the spec."""
        }]
    )

    manifest.spec_doc = response.content[0].text
    manifest.status = PipelineStatus.AWAITING_SPEC_APPROVAL
    return manifest