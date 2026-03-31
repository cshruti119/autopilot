# main.py
import asyncio, redis, json, os
from core.pipeline import build_graph
from agents.orchestrator.agent import run as orchestrate
from agents.codebase_intel.agent import index_repo
from dotenv import load_dotenv

load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL"))

def run_pipeline(jira_id: str):
    # Step 1: Index the repo (idempotent)
    index_repo(os.getenv("TARGET_REPO_PATH"))

    # Step 2: Orchestrator builds manifest
    manifest = orchestrate(jira_id)
    r.set(f"manifest:{jira_id}", manifest.model_dump_json())

    # Step 3: Run LangGraph pipeline
    graph = build_graph()
    final = graph.invoke(manifest)

    print(f"\n✅ Pipeline complete. Status: {final.status}")
    if final.status == "escalated":
        print(f"⚠️  Escalated: {final.failure_reason}")

if __name__ == "__main__":
    run_pipeline("TIC-1")   # Your Jira story ID