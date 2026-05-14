# Autopilot

An AI-driven pipeline that reads Jira stories and generates code, tests, and GitHub PRs using a multi-agent architecture.

## Requirements

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- [Colima](https://github.com/abiosoft/colima) + Docker
- Node.js 18+

## Setup

```bash
# Install Python deps
uv sync

# Install Vue deps
cd checkpoints/ui/frontend && npm install && cd ../../..
```

Copy `.env` and fill in your keys:
```
GEMINI_API_KEY=...
GITHUB_TOKEN=...
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://aifsd:aifsd@localhost:5432/aifsd
GITHUB_REPO=owner/repo
TARGET_REPO_PATH=/path/to/target/repo
```

## Running the Checkpoint UI

```bash
# 1. Start infrastructure
colima start
docker-compose up -d

# 2. Populate the DB (runs orchestrator + prep agents)
uv run python demo_agents.py

# 3. Terminal 1 — FastAPI server
uv run uvicorn checkpoints.ui.server:app --host 127.0.0.1 --port 8990 --reload

# 4. Terminal 2 — Vue dev server
cd checkpoints/ui/frontend && npm run dev

# 5. Open in browser
# http://localhost:5173/?jira_id=TT-1
```

## Other Commands

```bash
uv run pytest        # run tests
uv run black .       # format
uv run flake8        # lint
```
