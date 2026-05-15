# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**Autopilot** is an AI-driven software development pipeline that reads Jira stories and automatically generates code, tests, and GitHub pull requests using a multi-agent architecture.

## Commands

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies (requires Node 20+)
cd checkpoints/ui/frontend && npm install

# Start required infrastructure (Redis, Postgres)
colima start
docker-compose up -d

# Populate DB and run orchestrator + prep agents
uv run python demo_agents.py

# Start the agent API + checkpoint UI server
uv run uvicorn checkpoints.ui.server:app --host 127.0.0.1 --port 8990 --reload

# Start frontend dev server
cd checkpoints/ui/frontend && npm run dev
# Open: http://localhost:5173/?jira_id=TT-1

# Run tests
uv run pytest

# Lint / Format
uv run flake8
uv run black .
```

## Required Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Orchestrator and prep agents |
| `GITHUB_TOKEN` | Repo setup and PR agent |
| `REDIS_URL` | State caching (`redis://localhost:6379`) |
| `POSTGRES_URL` | `postgresql://aifsd:aifsd@localhost:5432/aifsd` |
| `GITHUB_ORG` | GitHub org or user to create repos under |
| `LOCAL_WORKSPACE` | Local directory where repos are cloned (e.g. `/tmp/autopilot_workspace`) |

## Architecture

### Hybrid Pipeline Flow

Code is generated and reviewed **locally** for security. Only the spec and final approved code are pushed to GitHub.

```
inputs/TT-1.md (Jira story)
    → Orchestrator        (extract requirements via Gemini)
    → Prep Agent          (generate SPEC.md via Gemini)
    → [Checkpoint 1: spec approval — UI at /?jira_id=TT-1]
    → Repo Setup Agent    (create GH repo if missing, commit SPEC.md, clone locally)
    → [TDD Loop — runs fully locally, MAX_RETRIES=3]
        → Test Agent      (reads local SPEC.md, generates/fixes tests)
        → Dev Agent       (reads local SPEC.md, generates/fixes code)
        → Review Agent    (runs tests + coverage locally, routes → test|dev|pass)
    → [On loop PASS: Review Agent syncs final SPEC.md back to Postgres]
    → [Checkpoint 2: review approval — UI shows test results + GH branch link]
    → Pull Request Agent  (pushes branch to GitHub, opens PR)
```

### Security Model

- Generated code **never leaves the local machine** until a human explicitly approves at Checkpoint 2.
- SPEC.md is committed to GitHub early (after Checkpoint 1) — it is not sensitive.
- The local workspace (`LOCAL_WORKSPACE`) is the sandbox for all code generation.

### Spec Lifecycle

```
Prep Agent → Postgres (checkpoint table)
    → Repo Setup Agent → SPEC.md committed to GH repo
    → Local agents read SPEC.md from local clone
    → [SPEC.md may be updated during TDD loop]
    → Review Agent (on pass) → syncs final SPEC.md back to Postgres
```

The spec + code living together in the GH repo serves as a **knowledge base** for future projects.

### Key Components

**`core/state/manifest.py`** — `TaskManifest` is the shared Pydantic state model. Tracks story data, spec, review results, retry count, and `PipelineStatus`.

**`core/pipeline.py`** — LangGraph state machine wiring all agents together.

**`agents/orchestrator.py`** — Reads Markdown stories from `inputs/`, extracts requirements via Gemini, saves to Redis.

**`agents/prep.py`** — Generates technical spec via Gemini. Saves to Postgres `checkpoint` table. Accepts optional `feedback` for revision.

**`agents/repo_setup/agent.py`** _(to build)_ — Creates GitHub repo if missing, commits `SPEC.md`, clones repo to `LOCAL_WORKSPACE/{jira_id}`.

**`agents/test_agent/agent.py`** — Reads `SPEC.md` from local repo, generates/fixes tests. Runs in context of local clone.

**`agents/dev/agent.py`** — Reads `SPEC.md` from local repo, generates/fixes implementation code. Language-agnostic — follows language specified in spec.

**`agents/review/agent.py`** — Runs tests + coverage locally. Acts as TDD loop router: points out failures and decides whether Test Agent or Dev Agent should retry. On pass, syncs final `SPEC.md` to Postgres.

**`agents/pr/agent.py`** _(to build)_ — Pushes local branch to GitHub, opens pull request.

**`checkpoints/ui/server.py`** — Single FastAPI server exposing all agent APIs and human checkpoint endpoints. Vue frontend connects to this.

**`checkpoints/db.py`** — Postgres CRUD for the `checkpoint` table (spec, story, ACs, tech details, status, feedback).

**`util.py`** — `getClient()` (Gemini via LangChain), `getRedisClient()` (with mock fallback).

### Agent API Endpoints (all on one FastAPI server)

Each agent exposes a trigger endpoint so the UI can start/monitor any step:

```
POST /api/agent/orchestrator/run
POST /api/agent/prep/run
POST /api/agent/repo-setup/run
POST /api/agent/test/run
POST /api/agent/dev/run
POST /api/agent/review/run
POST /api/agent/pr/run

GET  /api/checkpoint/{jira_id}
POST /api/checkpoint/{jira_id}/approve
POST /api/checkpoint/{jira_id}/reject
GET  /api/checkpoint/{jira_id}/status
```

### Models Used

- **Orchestrator, Prep**: Google Gemini (`gemini-3-flash-preview`)
- **Test, Dev, Review**: Claude Sonnet (`claude-sonnet-4-20250514`)
- **Repo Setup, PR**: PyGithub API

### Pipeline Statuses

```
INITIATED → PREPPING → AWAITING_SPEC_APPROVAL → SETTING_UP_REPO
    → WRITING_TESTS → DEVELOPING → REVIEWING
    → AWAITING_REVIEW_APPROVAL → CREATING_PR → DONE
```

On TDD loop failure: `REVIEWING → WRITING_TESTS | DEVELOPING` (up to MAX_RETRIES=3)
On escalation: `→ ESCALATED`

### Input Format

Stories go in `inputs/` as Markdown files (e.g., `TT-1.md`). They should include: project overview, user story, technical details, scope, and acceptance criteria in Given/When/Then format.
