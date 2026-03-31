# checkpoints/ui/server.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import redis, json

app = FastAPI()
r = redis.from_url("redis://localhost:6379")

@app.get("/checkpoint/{jira_id}", response_class=HTMLResponse)
def show_checkpoint(jira_id: str):
    raw = r.get(f"manifest:{jira_id}")
    manifest = json.loads(raw)
    return f"""
    <html><body>
      <h2>AIFSD Checkpoint — {jira_id}</h2>
      <h3>Status: {manifest['status']}</h3>
      <pre>{manifest.get('spec_doc', 'No spec yet')}</pre>
      <form method="POST" action="/approve/{jira_id}/spec">
        <button type="submit">✅ Approve Spec</button>
      </form>
      <form method="POST" action="/reject/{jira_id}/spec">
        <button type="submit">❌ Reject Spec</button>
      </form>
    </body></html>
    """

@app.post("/approve/{jira_id}/spec")
def approve_spec(jira_id: str):
    raw = r.get(f"manifest:{jira_id}")
    manifest = json.loads(raw)
    manifest["human_approved_spec"] = True
    r.set(f"manifest:{jira_id}", json.dumps(manifest))
    return {"status": "approved, pipeline resuming"}