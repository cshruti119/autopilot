# agents/test_agent/agent.py
import anthropic, os, json
from core.state.manifest import TaskManifest

client = anthropic.Anthropic()

def run(manifest: TaskManifest) -> TaskManifest:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{
            "role": "user",
            "content": f"""You are a QA Engineer writing tests BEFORE seeing the implementation.

Spec:
{manifest.spec_doc}

Acceptance Criteria:
{chr(10).join(manifest.acceptance_criteria)}

Write unit tests and integration tests. Return JSON where keys are 
test file paths and values are complete test file contents.
Return ONLY valid JSON."""
        }]
    )

    manifest.generated_tests = json.loads(response.content[0].text)
    return manifest