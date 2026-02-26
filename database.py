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


async def init_db():
    """Initialize database schema and seed demo data if empty."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
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
            )
        """)
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
