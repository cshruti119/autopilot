import os
import subprocess

from github import Github, GithubException

from core.state.manifest import TaskManifest, PipelineStatus
from util import getClient

_AGENT_MD_PROMPTS = {
    "test": """You are writing TEST_AGENT.md — instructions for an AI test agent working on this project.
Include: test framework and language, what to test (based on spec tasks), file/folder conventions, naming patterns.
Be specific to this project. Use markdown. Be concise.""",

    "dev": """You are writing DEV_AGENT.md — instructions for an AI developer agent working on this project.
Include: language and frameworks (from spec), file structure, implementation patterns, what NOT to do.
Be specific to this project. Use markdown. Be concise.""",

    "review": """You are writing REVIEW_AGENT.md — instructions for an AI review agent working on this project.
Include: how to run tests for this stack, coverage requirements, what to check, how to decide if failures are in tests vs implementation.
Be specific to this project. Use markdown. Be concise.""",
}


def _generate_agent_md(agent: str, spec_content: str) -> str:
    client = getClient()
    messages = [
        ("system", _AGENT_MD_PROMPTS[agent]),
        ("user", f"Spec:\n{spec_content}"),
    ]
    response = client.invoke(messages)
    return response.text


def run(manifest: TaskManifest) -> TaskManifest:
    token = os.getenv("GITHUB_TOKEN")
    org = os.getenv("GITHUB_ORG")
    workspace = os.getenv("LOCAL_WORKSPACE", "/tmp/autopilot_workspace")

    g = Github(token)
    owner = g.get_organization(org) if org else g.get_user()

    repo_name = manifest.jira_id.lower().replace("_", "-")
    manifest.repo_name = repo_name

    # Create repo if it doesn't exist
    try:
        repo = owner.get_repo(repo_name)
        print(f"✅ Repo {repo_name} already exists")
    except GithubException:
        repo = owner.create_repo(
            repo_name,
            private=True,
            auto_init=True,
            description=f"Autopilot generated repo for {manifest.jira_id}",
        )
        print(f"✅ Created repo {repo_name}")

    spec_content = manifest.spec_doc or ""

    # Commit SPEC.md
    _upsert_file(repo, "SPEC.md", spec_content, f"Add SPEC.md for {manifest.jira_id}")

    # Generate and commit agent MD files for each selected agent
    for agent in manifest.selected_agents:
        filename = f"{agent.upper()}_AGENT.md"
        print(f"🤖 Generating {filename}...")
        content = _generate_agent_md(agent, spec_content)
        _upsert_file(repo, filename, content, f"Add {filename}")
        print(f"✅ Committed {filename}")

    # Clone or pull locally
    os.makedirs(workspace, exist_ok=True)
    local_path = os.path.join(workspace, repo_name)
    clone_url = f"https://{token}@github.com/{repo.full_name}.git"

    if os.path.exists(os.path.join(local_path, ".git")):
        subprocess.run(["git", "-C", local_path, "pull"], check=True)
        print(f"✅ Pulled latest into {local_path}")
    else:
        subprocess.run(["git", "clone", clone_url, local_path], check=True)
        print(f"✅ Cloned repo to {local_path}")

    manifest.repo_local_path = local_path
    manifest.status = PipelineStatus.WRITING_TESTS
    return manifest


def _upsert_file(repo, path: str, content: str, message: str):
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
    except GithubException:
        repo.create_file(path, message, content)
