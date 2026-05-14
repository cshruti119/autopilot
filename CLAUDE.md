# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**Autopilot** is an AI-driven software development pipeline that reads Jira stories and automatically generates code, tests, and GitHub pull requests. It uses a multi-agent architecture built on LangGraph.

## Commands

```bash
# Install dependencies
uv sync

# Start required infrastructure (Redis, Postgres, ChromaDB)
docker-compose up -d

# Run the full pipeline
python main.py

# Run checkpoint approval UI (for spec/code approval)
uvicorn checkpoints.ui.server:app --port 8080

# Run tests
uv run pytest

# Lint
uv run flake8

# Format
uv run black .
```

## Required Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Orchestrator and prep agents |
| `GITHUB_TOKEN` | Commit agent for PR creation |
| `REDIS_URL` | State caching (`redis://localhost:6379`) |
| `POSTGRES_URL` | `postgresql://aifsd:aifsd@localhost:5432/aifsd` |
| `TARGET_REPO_PATH` | Path to the target repository to modify |
| `GITHUB_REPO` | `owner/repo` for PR creation |

## Architecture

### Pipeline Flow

```
inputs/TT-1.md (Jira story)
    → Orchestrator   (extract requirements via Gemini)
    → Prep           (generate technical spec via Gemini/Claude)
    → [Human Checkpoint: spec approval at /checkpoint/{jira_id}]
    → Dev            (generate code via Claude Sonnet)
    → Test           (generate tests via Claude Sonnet)
    → Review         (flake8 + pytest + 80% coverage gate)
    → Remediation    (route failures: back to dev/prep, or escalate)
    → Commit         (create GitHub branch + PR)
```

### Key Components

**`core/state/manifest.py`** — `TaskManifest` is the shared Pydantic state model passed through the entire LangGraph pipeline. It tracks everything: extracted story data, generated spec/code/tests, review results, retry count, and `PipelineStatus` enum.

**`core/pipeline.py`** — LangGraph state machine that wires all agents together and defines routing logic between nodes.

**`agents/orchestrator.py`** — Reads Markdown stories from `inputs/`, uses Gemini to extract acceptance criteria, affected codebases, tech details, and out-of-scope items. Results stored in Redis.

**`agents/prep.py`** — Queries ChromaDB for relevant codebase context, then generates a detailed technical spec. Sets status to `AWAITING_SPEC_APPROVAL`.

**`agents/codebase_intel.py`** — Indexes codebase files into ChromaDB for semantic search. Used by prep to understand existing code.

**`agents/dev/agent.py`** — Generates implementation code as `{filepath: content}` JSON. Writes to `/tmp/aifsd_sandbox_{jira_id}`.

**`agents/test_agent/agent.py`** — Generates unit/integration tests as `{test_filepath: content}` JSON using TDD approach.

**`agents/review/agent.py`** — Runs flake8 and pytest with coverage. Requires ≥80% coverage to pass.

**`agents/remediation/agent.py`** — Routes failures: "dev" (fix code), "prep" (fix spec), or "escalate". MAX_RETRIES=2.

**`agents/commit/agent.py`** — Creates branch `aifsd/{jira_id.lower()}`, commits sandbox files, opens GitHub PR.

**`checkpoints/ui/server.py`** — FastAPI server for human-in-the-loop approval. Reads pending specs from Redis, resumes pipeline on approve/reject.

**`util.py`** — Factory functions: `getClient()` (Gemini), `getChromaClient()` (ChromaDB at localhost:8001), `getRedisClient()` (with mock fallback).

### Models Used

- **Orchestrator, Prep**: Google Gemini (`gemini-2.0-flash`)
- **Dev, Test, Remediation, Review**: Claude Sonnet (`claude-sonnet-4-20250514`)
- **Commit**: PyGithub API

### Pipeline Statuses

`INITIATED → PREPPING → AWAITING_SPEC_APPROVAL → DEVELOPING → RECONCILING → REVIEWING → COMMITTING → DONE`

On failure: `→ REMEDIATING → (back to PREPPING or DEVELOPING) | ESCALATED`

### Input Format

Stories go in `inputs/` as Markdown files (e.g., `TT-1.md`). They should include: project overview, user story, technical details, scope, and acceptance criteria in Given/When/Then format.
