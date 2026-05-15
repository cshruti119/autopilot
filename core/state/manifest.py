from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class PipelineStatus(str, Enum):
    INITIATED = "initiated"
    PREPPING = "prepping"
    AWAITING_SPEC_APPROVAL = "awaiting_spec_approval"
    SETTING_UP_REPO = "setting_up_repo"
    WRITING_TESTS = "writing_tests"
    DEVELOPING = "developing"
    REVIEWING = "reviewing"
    AWAITING_REVIEW_APPROVAL = "awaiting_review_approval"
    CREATING_PR = "creating_pr"
    DONE = "done"
    ESCALATED = "escalated"


class ReviewResult(BaseModel):
    passed: bool
    issues: List[str]
    coverage: float
    route: str = "pass"  # "test" | "dev" | "pass"
    raw_output: str = ""


class TaskManifest(BaseModel):
    jira_id: str
    story_text: Optional[str] = ""
    acceptance_criteria: List[str] = []
    affected_codebases: List[dict] = []
    tech_details: List[str] = []
    out_of_scope: List[str] = []
    spec_doc: Optional[str] = None
    selected_agents: List[str] = ["test", "dev", "review"]
    repo_name: Optional[str] = None
    repo_local_path: Optional[str] = None
    generated_code: Optional[dict] = None
    generated_tests: Optional[dict] = None
    review_result: Optional[ReviewResult] = None
    retry_count: int = 0
    status: PipelineStatus = PipelineStatus.INITIATED
    human_approved_spec: bool = False
    human_approved_review: bool = False
    failure_reason: Optional[str] = None
