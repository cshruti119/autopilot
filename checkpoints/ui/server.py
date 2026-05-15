import os

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from checkpoints.db import (
    approve_checkpoint,
    create_table,
    get_checkpoint,
    reject_checkpoint,
    save_checkpoint,
    set_status,
)
from core.state.manifest import TaskManifest, PipelineStatus
import agents.prep as prep
import agents.repo_setup.agent as repo_setup
import agents.test_agent.agent as test_agent
import agents.dev.agent as dev_agent
import agents.review.agent as review_agent
import agents.pr.agent as pr_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

create_table()

# ── Request models ────────────────────────────────────────────────────────────

class RejectRequest(BaseModel):
    feedback: str


# ── Checkpoint endpoints ──────────────────────────────────────────────────────

@app.get("/api/checkpoint/{jira_id}")
def get_checkpoint_data(jira_id: str):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return dict(row)


@app.post("/api/checkpoint/{jira_id}/approve")
def approve_spec(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    approve_checkpoint(jira_id)
    background_tasks.add_task(run_post_spec_pipeline, jira_id, dict(row))
    return {"status": "approved", "message": "Spec approved. Pipeline resuming."}


@app.post("/api/checkpoint/{jira_id}/reject")
def reject_spec(jira_id: str, body: RejectRequest, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    reject_checkpoint(jira_id, body.feedback)
    background_tasks.add_task(rerun_prep, jira_id, body.feedback, dict(row))
    return {"status": "rejected", "message": "Feedback saved. Re-running prep agent."}


@app.post("/api/checkpoint/{jira_id}/approve-review")
def approve_review(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    set_status(jira_id, "creating_pr")
    background_tasks.add_task(run_pr_agent, jira_id, dict(row))
    return {"status": "creating_pr", "message": "Review approved. Creating pull request."}


@app.get("/api/checkpoint/{jira_id}/status")
def get_status_endpoint(jira_id: str):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"status": row["status"]}


# ── Individual agent trigger endpoints ───────────────────────────────────────

@app.post("/api/agent/orchestrator/run")
def trigger_orchestrator(background_tasks: BackgroundTasks, jira_id: str):
    from agents.orchestrator import run as orch_run
    background_tasks.add_task(orch_run, jira_id)
    return {"message": f"Orchestrator started for {jira_id}"}


@app.post("/api/agent/prep/run")
def trigger_prep(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    background_tasks.add_task(rerun_prep, jira_id, None, dict(row))
    return {"message": f"Prep agent started for {jira_id}"}


@app.post("/api/agent/repo-setup/run")
def trigger_repo_setup(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    manifest = _manifest_from_row(dict(row))
    background_tasks.add_task(repo_setup.run, manifest)
    return {"message": f"Repo setup agent started for {jira_id}"}


@app.post("/api/agent/test/run")
def trigger_test_agent(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    manifest = _manifest_from_row(dict(row))
    set_status(jira_id, "writing_tests")
    background_tasks.add_task(test_agent.run, manifest)
    return {"message": f"Test agent started for {jira_id}"}


@app.post("/api/agent/dev/run")
def trigger_dev_agent(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    manifest = _manifest_from_row(dict(row))
    set_status(jira_id, "developing")
    background_tasks.add_task(dev_agent.run, manifest)
    return {"message": f"Dev agent started for {jira_id}"}


@app.post("/api/agent/review/run")
def trigger_review_agent(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    manifest = _manifest_from_row(dict(row))
    set_status(jira_id, "reviewing")
    background_tasks.add_task(review_agent.run, manifest)
    return {"message": f"Review agent started for {jira_id}"}


@app.post("/api/agent/pr/run")
def trigger_pr_agent(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    background_tasks.add_task(run_pr_agent, jira_id, dict(row))
    return {"message": f"PR agent started for {jira_id}"}


# ── Background task implementations ──────────────────────────────────────────

def _manifest_from_row(row: dict) -> TaskManifest:
    return TaskManifest(
        jira_id=row["jira_id"],
        story_text=row.get("story_text", ""),
        acceptance_criteria=row.get("acceptance_criteria") or [],
        tech_details=row.get("tech_details") or [],
        affected_codebases=row.get("affected_codebases") or [],
        spec_doc=row.get("spec_doc"),
        status=PipelineStatus.PREPPING,
    )


def rerun_prep(jira_id: str, feedback, row: dict):
    set_status(jira_id, "processing")
    manifest = _manifest_from_row(row)
    manifest.status = PipelineStatus.PREPPING
    updated = prep.run(manifest, feedback=feedback)
    save_checkpoint(updated)


def run_post_spec_pipeline(jira_id: str, row: dict):
    """Repo setup → single pass through selected agents → await review approval."""
    set_status(jira_id, "setting_up_repo")
    manifest = _manifest_from_row(row)
    manifest.selected_agents = row.get("selected_agents") or ["test", "dev", "review"]

    try:
        manifest = repo_setup.run(manifest)
    except Exception as e:
        print(f"❌ Repo setup failed: {e}")
        set_status(jira_id, "escalated")
        return

    agents = manifest.selected_agents

    if "test" in agents:
        set_status(jira_id, "writing_tests")
        manifest = test_agent.run(manifest)

    if "dev" in agents:
        set_status(jira_id, "developing")
        manifest = dev_agent.run(manifest)

    if "review" in agents:
        set_status(jira_id, "reviewing")
        manifest = review_agent.run(manifest)
        set_status(jira_id, "awaiting_review_approval")
    else:
        set_status(jira_id, "awaiting_review_approval")


def run_pr_agent(jira_id: str, row: dict):
    set_status(jira_id, "creating_pr")
    manifest = _manifest_from_row(row)
    manifest.repo_name = jira_id.lower().replace("_", "-")
    workspace = os.getenv("LOCAL_WORKSPACE", "/tmp/autopilot_workspace")
    manifest.repo_local_path = os.path.join(workspace, manifest.repo_name)
    try:
        pr_agent.run(manifest)
        set_status(jira_id, "done")
    except Exception as e:
        print(f"❌ PR agent failed: {e}")
        set_status(jira_id, "escalated")


# ── Serve built Vue files in production ──────────────────────────────────────

_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
if os.path.exists(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
