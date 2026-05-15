import json
import os
import subprocess

from checkpoints.db import get_checkpoint, save_checkpoint
from core.state.manifest import TaskManifest, PipelineStatus, ReviewResult
from util import getClient

_TEST_COMMANDS = {
    "pom.xml":          ["mvn", "test", "-q"],
    "build.gradle":     ["gradle", "test", "-q"],
    "package.json":     ["npm", "test", "--", "--watchAll=false"],
    "go.mod":           ["go", "test", "./..."],
    "pyproject.toml":   ["python", "-m", "pytest", "--tb=short", "-q"],
    "requirements.txt": ["python", "-m", "pytest", "--tb=short", "-q"],
}


def _detect_test_command(local_path: str):
    for marker, cmd in _TEST_COMMANDS.items():
        if os.path.exists(os.path.join(local_path, marker)):
            return cmd
    return None


def _run_tests(local_path: str) -> tuple:
    cmd = _detect_test_command(local_path)
    if not cmd:
        return False, "Could not detect test command from project structure."
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=local_path, timeout=300)
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


def _analyse_with_llm(spec_content: str, agent_instructions: str, test_output: str) -> tuple:
    client = getClient()
    response = client.invoke([
        ("system", agent_instructions),
        ("user", f"""Review the following test output against the spec.

Spec:
{spec_content}

Test output:
{test_output}

Respond with valid JSON only:
{{
  "route": "test" | "dev" | "pass",
  "feedback": "specific actionable feedback for the agent that should fix this"
}}
- "test": the tests themselves are wrong or incomplete
- "dev": the implementation is wrong or missing
- "pass": everything looks good"""),
    ])
    parsed = json.loads(response.text)
    return parsed["route"], parsed.get("feedback", "")


def run(manifest: TaskManifest) -> TaskManifest:
    local_path = manifest.repo_local_path

    spec_content = _read_file(local_path, "SPEC.md")
    agent_instructions = _read_file(local_path, "REVIEW_AGENT.md")

    passed, raw_output = _run_tests(local_path)

    if passed:
        route, feedback = "pass", ""
    else:
        route, feedback = _analyse_with_llm(spec_content, agent_instructions, raw_output)

    manifest.review_result = ReviewResult(
        passed=passed or route == "pass",
        issues=[feedback] if feedback else [],
        coverage=0.0,
        route=route,
        raw_output=raw_output,
    )

    if route == "pass":
        # Sync final SPEC.md back to Postgres
        row = get_checkpoint(manifest.jira_id)
        if row:
            from core.state.manifest import TaskManifest as TM
            updated = TM(**{**dict(row), "spec_doc": spec_content})
            save_checkpoint(updated)
            print(f"✅ Synced final SPEC.md to Postgres for {manifest.jira_id}")
        manifest.status = PipelineStatus.AWAITING_REVIEW_APPROVAL
    else:
        manifest.status = (
            PipelineStatus.WRITING_TESTS if route == "test" else PipelineStatus.DEVELOPING
        )

    print(f"🔍 Review: route={route}, passed={manifest.review_result.passed}")
    return manifest


def _read_file(base: str, filename: str) -> str:
    path = os.path.join(base, filename)
    if not os.path.exists(path):
        return f"(No {filename} found)"
    with open(path) as f:
        return f.read()
