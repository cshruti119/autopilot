#!/usr/bin/env python3
"""
Demo script to test orchestrator and prep agents working together.
This shows the output from each agent to help evaluate their performance.
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import agents.orchestrator.agent as orchestrator
import agents.prep.agent as prep

console = Console()

def print_section(title: str, content: str, syntax: str = None):
    """Print a formatted section with title and content."""
    if syntax:
        content_display = Syntax(content, syntax, theme="monokai", line_numbers=True)
    else:
        content_display = content
    
    console.print(Panel(content_display, title=title, border_style="blue"))

def print_manifest_summary(manifest, title: str):
    """Print a summary of the manifest in a table format."""
    table = Table(title=title)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Jira ID", manifest.jira_id)
    table.add_row("Status", manifest.status)
    table.add_row("Acceptance Criteria Count", str(len(manifest.acceptance_criteria)))
    table.add_row("Affected Codebases", str(len(manifest.affected_codebases)))
    table.add_row("Has Spec", "Yes" if manifest.spec_doc else "No")
    
    console.print(table)

def demo_orchestrator_agent(jira_id: str = "TT-1"):
    """Demonstrate the orchestrator agent."""
    console.print("\n[bold yellow]🚀 STEP 1: Running Orchestrator Agent[/bold yellow]")
    console.print(f"Processing Jira ID: {jira_id}")
    
    try:
        manifest = orchestrator.run(jira_id)
        
        print_manifest_summary(manifest, "📋 Orchestrator Output Summary")
        
        # Show acceptance criteria
        if manifest.acceptance_criteria:
            criteria_text = "\n".join([f"• {criteria}" for criteria in manifest.acceptance_criteria])
            print_section("✅ Extracted Acceptance Criteria", criteria_text)
        
        # Show affected codebases
        if manifest.affected_codebases:
            codebases_text = json.dumps(manifest.affected_codebases, indent=2)
            print_section("📁 Affected Codebases", codebases_text, "json")
        
        # Show tech details
        if manifest.tech_details:
            print_section("🔧 Technical Details", str(manifest.tech_details))
        
        return manifest
        
    except Exception as e:
        console.print(f"[red]❌ Error in orchestrator agent: {e}[/red]")
        return None

def demo_prep_agent(manifest):
    """Demonstrate the prep agent."""
    if not manifest:
        console.print("[red]❌ Cannot run prep agent - no manifest provided[/red]")
        return None
        
    console.print("\n[bold yellow]🔧 STEP 2: Running Prep Agent[/bold yellow]")
    console.print("Generating detailed specification...")
    
    try:
        updated_manifest = prep.run(manifest)
        
        print_manifest_summary(updated_manifest, "📝 Prep Agent Output Summary")
        
        # Show the generated spec
        if updated_manifest.spec_doc:
            print_section("📋 Generated Specification", updated_manifest.spec_doc, "markdown")
        
        return updated_manifest
        
    except Exception as e:
        console.print(f"[red]❌ Error in prep agent: {e}[/red]")
        return None

def main():
    """Main demo function."""
    console.print(Panel.fit(
        "[bold green]Agent Performance Demo[/bold green]\n"
        "Testing Orchestrator → Prep Agent Pipeline",
        border_style="green"
    ))
    
    # Step 1: Run orchestrator
    manifest = demo_orchestrator_agent()
    
    if manifest:
        # Step 2: Run prep agent
        final_manifest = demo_prep_agent(manifest)
        
        if final_manifest:
            console.print("\n[bold green]✅ PIPELINE COMPLETED SUCCESSFULLY![/bold green]")
            console.print("Both agents ran successfully and produced output.")
        else:
            console.print("\n[bold red]⚠️ PIPELINE PARTIALLY COMPLETED[/bold red]")
            console.print("Orchestrator succeeded, but prep agent failed.")
    else:
        console.print("\n[bold red]❌ PIPELINE FAILED[/bold red]")
        console.print("Orchestrator agent failed to process the input.")

if __name__ == "__main__":
    main()