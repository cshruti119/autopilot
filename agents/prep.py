from agents.codebase_intel import query_context
from core.state.manifest import TaskManifest, PipelineStatus
from langchain_google_genai import ChatGoogleGenerativeAI
from util import getGeminiApiKey

def run(manifest: TaskManifest) -> TaskManifest:
    context = query_context(manifest.story_text)
    client = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", api_key=getGeminiApiKey())
    messages = [
        ("system", "You are a Tech Lead who knows about the project's codebase and architecture."),
        ("user", f"""         
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

Be precise. No code yet, just the spec.
""")
    ]

    response = client.invoke(messages)

    manifest.spec_doc = response.text
    manifest.status = PipelineStatus.AWAITING_SPEC_APPROVAL
    return manifest

if __name__ == "__main__":
    # For testing the agent independently
    print("Testing prep agent...")
    manifest = TaskManifest(
        jira_id="TT-1",
        status=PipelineStatus.INITIATED,
    )
    updated_manifest = run(manifest)
    print(updated_manifest.spec_doc)