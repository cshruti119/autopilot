#!/usr/bin/env python3
"""
Simple pipeline runner to test agents in sequence.
"""

from core.state.manifest import TaskManifest, PipelineStatus
import agents.orchestrator as orchestrator
import agents.prep as prep

def run_pipeline(jira_id: str = "TT-1"):
    """Run the agent pipeline and show outputs."""
    print(f"\n{'='*50}")
    print(f"🚀 STARTING PIPELINE FOR: {jira_id}")
    print(f"{'='*50}")
    
    # Step 1: Orchestrator
    print("\n📋 STEP 1: Orchestrator Agent")
    print("-" * 30)
    try:
        manifest = orchestrator.run(jira_id)
        print(f"✅ Status: {manifest.status}")
        print(f"📝 Acceptance Criteria: {len(manifest.acceptance_criteria)} items")
        print(f"📁 Affected Codebases: {len(manifest.affected_codebases)} items")
        
        # Show first few acceptance criteria
        if manifest.acceptance_criteria:
            print("\n🎯 Sample Acceptance Criteria:")
            for i, criteria in enumerate(manifest.acceptance_criteria[:3]):
                print(f"   {i+1}. {criteria[:100]}{'...' if len(criteria) > 100 else ''}")
    
    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        return None
        
    # Step 2: Prep Agent
    print(f"\n🔧 STEP 2: Prep Agent")
    print("-" * 30)
    try:
        manifest = prep.run(manifest)
        print(f"✅ Status: {manifest.status}")
        print(f"📋 Spec Generated: {'Yes' if manifest.spec_doc else 'No'}")
        
        # Show spec preview
        if manifest.spec_doc:
            # print(manifest.spec_doc)  # Show first 500 chars of spec
            spec_lines = manifest.spec_doc.split('\n')[:10] if manifest.spec_doc else []
            print("\n📄 Spec Preview (first 10 lines):")
            for line in spec_lines:
                print(f"   {line}")
            
            if manifest.spec_doc and len(manifest.spec_doc.split('\n')) > 10:
                print("   ... (truncated)")
    
    except Exception as e:
        print(f"❌ Prep agent failed: {e}")
        return manifest
        
    print(f"\n{'='*50}")
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"{'='*50}")
    
    return manifest

if __name__ == "__main__":
    final_manifest = run_pipeline()