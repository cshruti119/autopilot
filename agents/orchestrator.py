from core.state.manifest import TaskManifest, PipelineStatus
import json
from util import getClient, getRedisClient
import os,re 

client = getClient()
redis_client = getRedisClient()

def run(jira_id: str) -> TaskManifest:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
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
        - tech_details: any technical details or hints mentioned in the story that could help in implementation. Include Non-functional requirements as well mentioned in any section of the story.
        - out_of_scope: if mentioned in the story, extract them as a list. If not mentioned, return an empty list.
        Story:
        {story_text}

        Return only valid JSON."""
        )
    ]
    response = client.invoke(messages)
    json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
    parsed = json.loads(json_str)

    # Save to Redis with error handling
    try:
        print(f"🔄 Attempting to save data to Redis for {jira_id}")
        
        # Test Redis connection first
        redis_client.ping()
        print("✅ Redis connection successful")
        
        # Prepare data for Redis
        tech_details_value = parsed.get("tech_details", parsed.get("tech details", ""))
        out_of_scope_value = parsed.get("out_of_scope", parsed.get("out of scope items", []))
        
        redis_data = {
            "jira_id": jira_id,
            "story_text": story_text[:1000],  # Truncate long text for Redis
            "acceptance_criteria": json.dumps(parsed["acceptance_criteria"]),
            "affected_codebases": json.dumps(parsed["affected_codebases"]),
            "tech_details": json.dumps([tech_details_value] if isinstance(tech_details_value, str) else tech_details_value),
            "out_of_scope": json.dumps(out_of_scope_value)
        }
        
        # Save to Redis
        redis_key = f"orchestrator:{jira_id}"
        redis_client.hset(redis_key, mapping=redis_data)
        
        # Verify the save worked
        saved_data = redis_client.hgetall(redis_key)
        print(f"✅ Successfully saved orchestrator output to Redis. Keys: {list(saved_data.keys())}")
        
    except Exception as redis_error:
        print(f"❌ Redis save failed: {redis_error}")
        print(f"   Redis client: {redis_client}")
        print(f"   Error type: {type(redis_error)}")
        # Continue without Redis - don't fail the whole pipeline

    # Handle tech_details as list (required by TaskManifest)
    tech_details_value = parsed.get("tech_details", parsed.get("tech details", ""))
    if isinstance(tech_details_value, str):
        tech_details_list = [tech_details_value] if tech_details_value else []
    elif isinstance(tech_details_value, dict):
        tech_details_list = [f"{k}: {v}" for k, v in tech_details_value.items()]
    else:
        tech_details_list = tech_details_value or []
        
    return TaskManifest(
        jira_id=jira_id,
        story_text=story_text,
        acceptance_criteria=parsed["acceptance_criteria"],
        affected_codebases=parsed["affected_codebases"],
        tech_details=tech_details_list,
        out_of_scope=parsed.get("out_of_scope", parsed.get("out of scope items", [])),
        status=PipelineStatus.PREPPING
    )

if __name__ == "__main__":
    manifest = run("TT-1")
    print(manifest)