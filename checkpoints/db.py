import json
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv("POSTGRES_URL"))


def create_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint (
                    id SERIAL PRIMARY KEY,
                    jira_id VARCHAR(50) UNIQUE NOT NULL,
                    spec_doc TEXT,
                    story_text TEXT,
                    acceptance_criteria JSONB,
                    tech_details JSONB,
                    affected_codebases JSONB,
                    selected_agents JSONB DEFAULT '["test","dev","review"]',
                    status VARCHAR(30) DEFAULT 'pending',
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Add selected_agents column if table already exists without it
            cur.execute("""
                ALTER TABLE checkpoint
                ADD COLUMN IF NOT EXISTS selected_agents JSONB DEFAULT '["test","dev","review"]'
            """)


def save_checkpoint(manifest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO checkpoint
                    (jira_id, spec_doc, story_text, acceptance_criteria, tech_details,
                     affected_codebases, selected_agents, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (jira_id) DO UPDATE SET
                    spec_doc = EXCLUDED.spec_doc,
                    story_text = EXCLUDED.story_text,
                    acceptance_criteria = EXCLUDED.acceptance_criteria,
                    tech_details = EXCLUDED.tech_details,
                    affected_codebases = EXCLUDED.affected_codebases,
                    selected_agents = EXCLUDED.selected_agents,
                    status = 'pending',
                    feedback = NULL,
                    updated_at = NOW()
            """, (
                manifest.jira_id,
                manifest.spec_doc,
                manifest.story_text,
                json.dumps(manifest.acceptance_criteria),
                json.dumps(manifest.tech_details),
                json.dumps(manifest.affected_codebases),
                json.dumps(manifest.selected_agents),
            ))


def get_checkpoint(jira_id: str):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM checkpoint WHERE jira_id = %s", (jira_id,))
            return cur.fetchone()


def approve_checkpoint(jira_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE checkpoint SET status = 'approved', updated_at = NOW()
                WHERE jira_id = %s
            """, (jira_id,))


def reject_checkpoint(jira_id: str, feedback: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE checkpoint SET status = 'rejected', feedback = %s, updated_at = NOW()
                WHERE jira_id = %s
            """, (feedback, jira_id))


def set_status(jira_id: str, status: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE checkpoint SET status = %s, updated_at = NOW()
                WHERE jira_id = %s
            """, (status, jira_id))
