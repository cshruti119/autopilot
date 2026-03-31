# core/pipeline.py
from langgraph.graph import StateGraph, END
from core.state.manifest import TaskManifest, PipelineStatus
import agents.orchestrator.agent as orchestrator
import agents.prep.agent as prep
import agents.dev.agent as dev
import agents.test_agent.agent as test_agent
import agents.review.agent as review
import agents.remediation.agent as remediation
import agents.commit.agent as commit

def route_after_review(manifest: TaskManifest) -> str:
    if manifest.review_result and manifest.review_result.passed:
        return "commit"
    return "remediation"

def route_after_remediation(manifest: TaskManifest) -> str:
    if manifest.status == PipelineStatus.ESCALATED:
        return END
    if manifest.status == PipelineStatus.PREPPING:
        return "prep"
    return "dev"

def route_after_prep(manifest: TaskManifest) -> str:
    # Human checkpoint 1 — pause here for approval
    if not manifest.human_approved_spec:
        return "await_spec_approval"
    return "dev"

def build_graph():
    graph = StateGraph(TaskManifest)

    graph.add_node("prep", prep.run)
    graph.add_node("dev", dev.run)
    graph.add_node("test", test_agent.run)
    graph.add_node("review", review.run)
    graph.add_node("remediation", remediation.run)
    graph.add_node("commit", commit.run)

    graph.set_entry_point("prep")
    graph.add_conditional_edges("prep", route_after_prep,
                                {"dev": "dev", "await_spec_approval": END})
    graph.add_edge("dev", "review")    # test runs in parallel via FastAPI
    graph.add_conditional_edges("review", route_after_review,
                                {"commit": "commit", "remediation": "remediation"})
    graph.add_conditional_edges("remediation", route_after_remediation,
                                {"prep": "prep", "dev": "dev", END: END})
    graph.add_edge("commit", END)

    return graph.compile()