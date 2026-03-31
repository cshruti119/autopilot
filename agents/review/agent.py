# agents/review/agent.py
import subprocess, os, json
from core.state.manifest import TaskManifest, PipelineStatus, ReviewResult

def run(manifest: TaskManifest) -> TaskManifest:
    sandbox = f"/tmp/aifsd_sandbox_{manifest.jira_id}"
    issues = []

    # 1. Write tests into sandbox
    for filepath, content in (manifest.generated_tests or {}).items():
        full = os.path.join(sandbox, filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    # 2. Run linting
    lint = subprocess.run(
        ["python", "-m", "flake8", sandbox, "--max-line-length=100"],
        capture_output=True, text=True
    )
    if lint.returncode != 0:
        issues.append(f"Linting: {lint.stdout}")

    # 3. Run tests with coverage
    test_run = subprocess.run(
        ["python", "-m", "pytest", sandbox, "--cov", "--cov-report=json",
         "-q", "--tb=short"],
        capture_output=True, text=True, cwd=sandbox
    )
    coverage = 0.0
    try:
        with open(os.path.join(sandbox, "coverage.json")) as f:
            cov_data = json.load(f)
            coverage = cov_data["totals"]["percent_covered"]
    except:
        issues.append("Coverage report not generated")

    if coverage < 80:
        issues.append(f"Coverage {coverage:.1f}% is below 80% threshold")

    if test_run.returncode != 0:
        issues.append(f"Tests failed:\n{test_run.stdout}")

    passed = len(issues) == 0
    manifest.review_result = ReviewResult(
        passed=passed,
        issues=issues,
        coverage=coverage,
        breaking_changes=False  # extend with API diff tool later
    )
    manifest.status = (
        PipelineStatus.COMMITTING if passed else PipelineStatus.REMEDIATING
    )
    return manifest