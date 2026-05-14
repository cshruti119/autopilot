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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

create_table()


class RejectRequest(BaseModel):
    feedback: str


@app.get("/api/checkpoint/{jira_id}")
def get_checkpoint_data(jira_id: str):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return dict(row)


@app.post("/api/checkpoint/{jira_id}/approve")
def approve(jira_id: str, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    approve_checkpoint(jira_id)
    background_tasks.add_task(run_next_stage, jira_id)
    return {"status": "approved", "message": "Spec approved. Pipeline resuming."}


@app.post("/api/checkpoint/{jira_id}/reject")
def reject(jira_id: str, body: RejectRequest, background_tasks: BackgroundTasks):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    reject_checkpoint(jira_id, body.feedback)
    background_tasks.add_task(rerun_prep, jira_id, body.feedback, dict(row))
    return {"status": "rejected", "message": "Feedback saved. Re-running prep agent."}


@app.get("/api/checkpoint/{jira_id}/status")
def get_status(jira_id: str):
    row = get_checkpoint(jira_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"status": row["status"]}


def run_next_stage(jira_id: str):
    set_status(jira_id, "processing")
    print(f"\n🚀 Starting Step 4: Dev Agent for {jira_id}")
    # Dev agent will be wired here in the next pipeline stage
    set_status(jira_id, "approved")


def rerun_prep(jira_id: str, feedback: str, row: dict):
    set_status(jira_id, "processing")
    manifest = TaskManifest(
        jira_id=jira_id,
        story_text=row["story_text"],
        acceptance_criteria=row["acceptance_criteria"],
        tech_details=row["tech_details"],
        affected_codebases=row["affected_codebases"],
        status=PipelineStatus.PREPPING,
    )
    updated = prep.run(manifest, feedback=feedback)
    save_checkpoint(updated)


# Serve built Vue files in production
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend/dist")
if os.path.exists(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
