from core.state.manifest import TaskManifest, PipelineStatus
import json
from util import getClient
import os,re 

client = getClient()

def run(jira_id: str) -> TaskManifest:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    print(f"Root dir: {root_dir}")
    md_path = os.path.join(root_dir, f"inputs/{jira_id}.md")
    with open(md_path, "r") as f:
        story_text = f.read()

    messages = [
        ("system", "You are a helpful assistant that extracts structured information from Jira stories. The Jira story has 5 sections - Project Overview, User Story, Technical Details, In-scope and Out-of-scope, and Acceptance Criteria"),
        ("user", f"""Read the jira story and extract the following information. Return JSON with keys:
        Extract the following:
        - acceptance_criteria: a list of acceptance criteria
        - affected_codebases: a list of codebase folders likely to be affected based on the story. 
        If not mentioned, it could be that the repo doesn't exist, in that case return suggestion for repo names that might be relevant based on the story. 
        Also pass a field to say whether the repo exists or not. It should be inside the affected_codebases field as a dictionary with keys "repo_name" and "exists" (boolean).
        - tech details: any technical details or hints mentioned in the story that could help in implementation. Include Non-functional requirements as well mentioned in any section of the story.
        - out of scope items: if mentioned in the story, extract them as a list. If not mentioned, return an empty list.
        Story:
        {story_text}

        Return only valid JSON."""
        )
    ]
    response = client.invoke(messages)
    json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
    parsed = json.loads(json_str)

    return TaskManifest(
        jira_id=jira_id,
        story_text=story_text,
        acceptance_criteria=parsed["acceptance_criteria"],
        affected_codebases=parsed["affected_codebases"],
        tech_details=parsed.get("tech details", ""),  # Note: LLM returns "tech details" with space
        status=PipelineStatus.PREPPING
    )

if __name__ == "__main__":
    manifest = run("TT-1")
    print(manifest)