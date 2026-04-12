# core/pipeline.py
from langgraph.graph import StateGraph, END
from core.state.manifest import TaskManifest, PipelineStatus
import agents.orchestrator as orchestrator
import agents.prep as prep
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

    graph.add_node("orchestrate", orchestrator.run)
    graph.add_node("prep", prep.run)

    # Set the entry point and create a simple flow
    graph.set_entry_point("orchestrate")
    graph.add_edge("orchestrate", "prep")
    graph.add_edge("prep", END)

    return graph.compile()

def run_pipeline_graph(jira_id: str = "TT-1"):
    """Run the pipeline using the graph structure."""
    print(f"🚀 Starting pipeline for {jira_id}")
    
    # Create initial manifest
    initial_manifest = TaskManifest(
        jira_id=jira_id,
        status=PipelineStatus.INITIATED
    )
    
    # Build and run graph
    graph = build_graph()
    final_manifest = graph.invoke(initial_manifest)
    
    print(f"✅ Pipeline completed. Final status: {final_manifest.status}")
    return final_manifest

if __name__ == "__main__":
    # Run the pipeline when script is executed directly
    manifest = run_pipeline_graph("TT-1")
    print("\nFinal Manifest Summary:")
    print(f"- Jira ID: {manifest.jira_id}")
    print(f"- Status: {manifest.status}")
    print(f"- Acceptance Criteria: {len(manifest.acceptance_criteria)} items")
    print(f"- Has Spec: {'Yes' if manifest.spec_doc else 'No'}")
    #                             {"prep": "prep", "dev": "dev", END: END})
    # graph.add_edge("commit", END)

    return graph.compile()