# core/state/manifest.py
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class PipelineStatus(str, Enum):
    INITIATED = "initiated"
    PREPPING = "prepping"
    AWAITING_SPEC_APPROVAL = "awaiting_spec_approval"
    DEVELOPING = "developing"
    RECONCILING = "reconciling"
    AWAITING_CODE_APPROVAL = "awaiting_code_approval"
    REVIEWING = "reviewing"
    REMEDIATING = "remediating"
    COMMITTING = "committing"
    DONE = "done"
    ESCALATED = "escalated"

class ReviewResult(BaseModel):
    passed: bool
    issues: List[str]
    coverage: float
    breaking_changes: bool

class TaskManifest(BaseModel):
    jira_id: str
    story_text: Optional[str] = ""
    acceptance_criteria: List[str] = []
    affected_codebases: List[dict] = []
    tech_details: List[str] = []
    out_of_scope: List[str] = []
    spec_doc: Optional[str] = None
    generated_code: Optional[dict] = None   # filename -> content
    generated_tests: Optional[dict] = None
    review_result: Optional[ReviewResult] = None
    retry_count: int = 0
    status: PipelineStatus = PipelineStatus.INITIATED
    human_approved_spec: bool = False
    human_approved_code: bool = False
    failure_reason: Optional[str] = None