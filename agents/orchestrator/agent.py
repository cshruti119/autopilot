# agents/orchestrator/agent.py
from jira import JIRA
from core.state.manifest import TaskManifest, PipelineStatus
import anthropic, json, os

client = anthropic.Anthropic()

def run(jira_id: str) -> TaskManifest:
    # Connect to Jira and fetch story
    jira = JIRA(
        server=os.getenv("JIRA_URL"),
        basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
    )
    issue = jira.issue(jira_id)
    story_text = issue.fields.description or issue.fields.summary

    # Use Claude to extract structured info
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""Parse this Jira story and return JSON with keys:
            acceptance_criteria (list), affected_codebases (list of folder names).
            Story: {story_text}
            Return only valid JSON."""
        }]
    )

    parsed = json.loads(response.content[0].text)

    return TaskManifest(
        jira_id=jira_id,
        story_text=story_text,
        acceptance_criteria=parsed["acceptance_criteria"],
        affected_codebases=parsed["affected_codebases"],
        status=PipelineStatus.PREPPING
    )