"""
CaseCommand Database Layer
==========================
SQLite-backed persistence for cases, deadlines, and modules.
Uses aiosqlite for async operations.
"""

import os
import json
import aiosqlite
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("casecommand.db")

DB_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).parent / "casecommand.db"))

# ── Demo data for initial seeding ─────────────────
SEED_CASES = [
    {
        "id": "c1",
        "name": "Rodriguez v. Smith Trucking",
        "number": "24STCV12345",
        "type": "Personal Injury",
        "client": "Maria Rodriguez",
        "opposing": "Smith Trucking, Inc.",
        "phase": 3,
        "specials": 88000,
        "valuation": {"lo": 150, "mid": 275, "hi": 450},
        "deadline": {
            "date": "Mar 11",
            "text": "45-Day Discovery Motion",
            "urgent": True,
        },
        "modules": {
            "pleadings": {
                "status": "complete",
                "label": "5 COAs filed",
                "detail": "Negligence, MV Neg, Respondeat Superior, Neg Entrustment, Neg Per Se",
            },
            "discovery": {
                "status": "active",
                "label": "5 deficient responses",
                "detail": "M&C letter drafted",
            },
            "trial": {
                "status": "building",
                "label": "Cross: J. Smith (25 Qs)",
                "detail": "6 chapters, 15 source-linked",
            },
            "settlement": {
                "status": "monitoring",
                "label": "Post-discovery trigger",
                "detail": "Reassess after discovery",
            },
        },
    },
    {
        "id": "c2",
        "name": "Chen v. Pacific Properties",
        "number": "25STCV02890",
        "type": "Premises Liability",
        "client": "David Chen",
        "opposing": "Pacific Properties LLC",
        "phase": 2,
        "specials": 34500,
        "valuation": {"lo": 55, "mid": 95, "hi": 165},
        "deadline": {
            "date": "Mar 28",
            "text": "Defendant Response Due",
            "urgent": False,
        },
        "modules": {
            "pleadings": {
                "status": "complete",
                "label": "3 COAs filed",
                "detail": "Premises Liability, Negligence, Breach",
            },
            "discovery": {
                "status": "pending",
                "label": "After answer",
                "detail": "Prepare once defendant answers",
            },
            "settlement": {
                "status": "active",
                "label": "Demand sent: $85K",
                "detail": "Response due Mar 15",
            },
        },
    },
    {
        "id": "c3",
        "name": "Williams v. TechStart",
        "number": None,
        "type": "Employment — FEHA",
        "client": "Angela Williams",
        "opposing": "TechStart Inc.",
        "phase": 1,
        "specials": 128000,
        "valuation": {"lo": 200, "mid": 425, "hi": 750},
        "deadline": {
            "date": "Mar 1",
            "text": "Complete Intake & File",
            "urgent": True,
        },
        "modules": {
            "pleadings": {
                "status": "active",
                "label": "Analyzing 5 COAs",
                "detail": "WT, Discrim, Harassment, Retaliation, Breach",
            },
            "settlement": {
                "status": "assessing",
                "label": "High-value FEHA",
                "detail": "Recommend filing first for leverage",
            },
        },
    },
]


def _row_to_case(row: aiosqlite.Row) -> Dict:
    """Convert a database row to a case dict matching the API format."""
    return {
        "id": row["id"],
        "name": row["name"],
        "number": row["number"],
        "type": row["type"],
        "client": row["client"],
        "opposing": row["opposing"],
        "phase": row["phase"],
        "specials": row["specials"],
        "valuation": json.loads(row["valuation"]),
        "deadline": json.loads(row["deadline"]) if row["deadline"] else None,
        "modules": json.loads(row["modules"]) if row["modules"] else {},
    }


SCHEMA = """
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        number TEXT,
        type TEXT NOT NULL,
        client TEXT NOT NULL,
        opposing TEXT NOT NULL,
        phase INTEGER NOT NULL DEFAULT 0,
        specials INTEGER NOT NULL DEFAULT 0,
        valuation TEXT NOT NULL DEFAULT '{}',
        deadline TEXT,
        modules TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        case_id TEXT,
        doc_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending_review',
        created_by TEXT NOT NULL DEFAULT 'agent',
        review_note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        reviewed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        case_id TEXT,
        title TEXT NOT NULL,
        detail TEXT DEFAULT '',
        priority TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'open',
        due_date TEXT,
        created_by TEXT NOT NULL DEFAULT 'agent',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS deadlines (
        id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        title TEXT NOT NULL,
        rule TEXT DEFAULT '',
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        note TEXT DEFAULT '',
        created_by TEXT NOT NULL DEFAULT 'agent',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        detail TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS agent_runs (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'running',
        summary TEXT DEFAULT '',
        actions INTEGER DEFAULT 0,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        finished_at TEXT
    );
"""


async def init_db():
    """Initialize database schema and seed demo data if empty."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

        # Seed demo data if table is empty
        cursor = await db.execute("SELECT COUNT(*) FROM cases")
        count = (await cursor.fetchone())[0]
        if count == 0:
            logger.info("Seeding database with %d demo cases", len(SEED_CASES))
            for case in SEED_CASES:
                await db.execute(
                    """INSERT INTO cases (id, name, number, type, client, opposing, phase, specials, valuation, deadline, modules)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        case["id"],
                        case["name"],
                        case.get("number"),
                        case["type"],
                        case["client"],
                        case["opposing"],
                        case["phase"],
                        case["specials"],
                        json.dumps(case["valuation"]),
                        json.dumps(case.get("deadline")) if case.get("deadline") else None,
                        json.dumps(case.get("modules", {})),
                    ),
                )
            await db.commit()
            logger.info("Database seeded successfully")
        else:
            logger.info("Database already has %d cases", count)

        # Seed date-typed deadlines if empty (relative to today so the
        # autonomous paralegal has live work in the demo data)
        cursor = await db.execute("SELECT COUNT(*) FROM deadlines")
        if (await cursor.fetchone())[0] == 0:
            from datetime import date, timedelta
            today = date.today()
            seed_deadlines = [
                ("d1", "c1", "Motion to compel further discovery responses — JURISDICTIONAL",
                 "CCP §2030.300(c)", (today + timedelta(days=9)).isoformat(),
                 "45-day deadline; extendable only by written agreement"),
                ("d2", "c2", "Defendant's responsive pleading due",
                 "CCP §412.20(a)(3)", (today + timedelta(days=26)).isoformat(), ""),
                ("d3", "c3", "Complete intake and file complaint",
                 "CCP §335.1 (2-year SOL)", (today + timedelta(days=3)).isoformat(),
                 "High-value FEHA matter; file before SOL concerns arise"),
            ]
            for did, cid, title, rule, due, note in seed_deadlines:
                await db.execute(
                    """INSERT INTO deadlines (id, case_id, title, rule, due_date, note, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, 'seed')""",
                    (did, cid, title, rule, due, note),
                )
            await db.commit()
            logger.info("Seeded %d demo deadlines", len(seed_deadlines))


async def get_all_cases() -> List[Dict]:
    """Retrieve all cases from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM cases ORDER BY created_at")
        rows = await cursor.fetchall()
        return [_row_to_case(row) for row in rows]


async def get_case(case_id: str) -> Optional[Dict]:
    """Retrieve a single case by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        return _row_to_case(row) if row else None


async def create_case(case_data: Dict) -> Dict:
    """Create a new case and return it."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO cases (id, name, number, type, client, opposing, phase, specials, valuation, deadline, modules)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_data["id"],
                case_data["name"],
                case_data.get("number"),
                case_data["type"],
                case_data["client"],
                case_data["opposing"],
                case_data.get("phase", 0),
                case_data.get("specials", 0),
                json.dumps(case_data.get("valuation", {"lo": 0, "mid": 0, "hi": 0})),
                json.dumps(case_data.get("deadline")) if case_data.get("deadline") else None,
                json.dumps(case_data.get("modules", {})),
            ),
        )
        await db.commit()
    return await get_case(case_data["id"])


async def update_case(case_id: str, updates: Dict) -> Optional[Dict]:
    """Update a case. Only updates provided fields."""
    existing = await get_case(case_id)
    if not existing:
        return None

    # Merge updates into existing
    for key in ("name", "number", "type", "client", "opposing", "phase", "specials"):
        if key in updates:
            existing[key] = updates[key]
    if "valuation" in updates:
        existing["valuation"] = updates["valuation"]
    if "deadline" in updates:
        existing["deadline"] = updates["deadline"]
    if "modules" in updates:
        existing["modules"] = updates["modules"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE cases SET
                name=?, number=?, type=?, client=?, opposing=?, phase=?, specials=?,
                valuation=?, deadline=?, modules=?, updated_at=datetime('now')
               WHERE id=?""",
            (
                existing["name"],
                existing.get("number"),
                existing["type"],
                existing["client"],
                existing["opposing"],
                existing["phase"],
                existing["specials"],
                json.dumps(existing["valuation"]),
                json.dumps(existing["deadline"]) if existing.get("deadline") else None,
                json.dumps(existing.get("modules", {})),
                case_id,
            ),
        )
        await db.commit()
    return await get_case(case_id)


async def delete_case(case_id: str) -> bool:
    """Delete a case. Returns True if deleted, False if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_case_count() -> int:
    """Get the total number of cases."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM cases")
        row = await cursor.fetchone()
        return row[0]


# ══════════════════════════════════════════════════
# Documents (drafted work product — attorney review gate)
# ══════════════════════════════════════════════════

def _rows_to_dicts(rows) -> List[Dict]:
    return [dict(r) for r in rows]


async def create_document(doc: Dict) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO documents (id, case_id, doc_type, title, content, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc["id"], doc.get("case_id"), doc["doc_type"], doc["title"],
             doc["content"], doc.get("status", "pending_review"),
             doc.get("created_by", "agent")),
        )
        await db.commit()
    return await get_document(doc["id"])


async def get_document(doc_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_documents(status: Optional[str] = None, case_id: Optional[str] = None) -> List[Dict]:
    query = "SELECT * FROM documents WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if case_id:
        query += " AND case_id = ?"
        params.append(case_id)
    query += " ORDER BY created_at DESC"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return _rows_to_dicts(await cursor.fetchall())


async def review_document(doc_id: str, status: str, note: str = "") -> Optional[Dict]:
    """Attorney review action: approve or reject a draft."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """UPDATE documents
               SET status = ?, review_note = ?, reviewed_at = datetime('now'),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (status, note, doc_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
    return await get_document(doc_id)


# ══════════════════════════════════════════════════
# Tasks (agent + attorney work items)
# ══════════════════════════════════════════════════

async def create_task(task: Dict) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO tasks (id, case_id, title, detail, priority, due_date, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task["id"], task.get("case_id"), task["title"],
             task.get("detail", ""), task.get("priority", "medium"),
             task.get("due_date"), task.get("created_by", "agent")),
        )
        await db.commit()
    return await get_task(task["id"])


async def get_task(task_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_tasks(status: Optional[str] = None, case_id: Optional[str] = None) -> List[Dict]:
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if case_id:
        query += " AND case_id = ?"
        params.append(case_id)
    query += (" ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1"
              " WHEN 'medium' THEN 2 ELSE 3 END, due_date IS NULL, due_date")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return _rows_to_dicts(await cursor.fetchall())


async def update_task_status(task_id: str, status: str) -> Optional[Dict]:
    completed = "datetime('now')" if status == "done" else "NULL"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"UPDATE tasks SET status = ?, completed_at = {completed} WHERE id = ?",
            (status, task_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
    return await get_task(task_id)


async def task_exists_for(case_id: str, title_like: str) -> bool:
    """Check whether an open task matching a title substring already exists
    for a case — used by the worker to avoid duplicate task creation."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM tasks
               WHERE case_id = ? AND status = 'open' AND title LIKE ?""",
            (case_id, f"%{title_like}%"),
        )
        row = await cursor.fetchone()
        return row[0] > 0


# ══════════════════════════════════════════════════
# Deadlines (date-typed, rule-cited)
# ══════════════════════════════════════════════════

async def create_deadline(dl: Dict) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO deadlines (id, case_id, title, rule, due_date, note, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dl["id"], dl["case_id"], dl["title"], dl.get("rule", ""),
             dl["due_date"], dl.get("note", ""), dl.get("created_by", "agent")),
        )
        await db.commit()
    return await get_deadline(dl["id"])


async def get_deadline(deadline_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM deadlines WHERE id = ?", (deadline_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_deadlines(
    status: str = "pending",
    within_days: Optional[int] = None,
    case_id: Optional[str] = None,
) -> List[Dict]:
    query = "SELECT * FROM deadlines WHERE status = ?"
    params: list = [status]
    if within_days is not None:
        query += " AND due_date <= date('now', ?)"
        params.append(f"+{within_days} days")
    if case_id:
        query += " AND case_id = ?"
        params.append(case_id)
    query += " ORDER BY due_date"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return _rows_to_dicts(await cursor.fetchall())


async def update_deadline_status(deadline_id: str, status: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE deadlines SET status = ? WHERE id = ?", (status, deadline_id)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
    return await get_deadline(deadline_id)


# ══════════════════════════════════════════════════
# Audit log (RPC 5.3 supervision trail)
# ══════════════════════════════════════════════════

async def log_audit(actor: str, action: str, target_type: str = "",
                    target_id: str = "", detail: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO audit_log (actor, action, target_type, target_id, detail)
               VALUES (?, ?, ?, ?, ?)""",
            (actor, action, target_type, target_id, detail[:2000]),
        )
        await db.commit()


async def list_audit(limit: int = 100) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        )
        return _rows_to_dicts(await cursor.fetchall())


# ══════════════════════════════════════════════════
# Agent runs (worker cycle history)
# ══════════════════════════════════════════════════

async def start_agent_run(run_id: str, kind: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO agent_runs (id, kind) VALUES (?, ?)", (run_id, kind)
        )
        await db.commit()


async def finish_agent_run(run_id: str, status: str, summary: str,
                           actions: int = 0, input_tokens: int = 0,
                           output_tokens: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE agent_runs
               SET status = ?, summary = ?, actions = ?, input_tokens = ?,
                   output_tokens = ?, finished_at = datetime('now')
               WHERE id = ?""",
            (status, summary[:2000], actions, input_tokens, output_tokens, run_id),
        )
        await db.commit()


async def list_agent_runs(limit: int = 20) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        return _rows_to_dicts(await cursor.fetchall())


async def get_last_agent_run(kind: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM agent_runs WHERE kind = ? ORDER BY started_at DESC LIMIT 1",
            (kind,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
