"""
CaseCommand — Calendar & Deadline Engine

Automatic deadline calculation from case events:
- Filing deadlines computed from complaint, motions, discovery
- Statutory deadlines (SOL, trial preference)
- Reminder scheduling
- Integration-ready for Google Calendar sync
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from src.config import get_settings


# ---------------------------------------------------------------------------
# California Litigation Deadline Rules
# ---------------------------------------------------------------------------

# Days to add for service method (CCP §1013)
SERVICE_EXTENSIONS = {
    "personal": 0,
    "mail": 5,     # CCP §1013(a) — 5 calendar days for CA mail
    "electronic": 2,  # CCP §1010.6(a)(4) — 2 court days
    "fax": 2,
    "overnight": 2,
}

LITIGATION_DEADLINES = {
    "complaint_filed": [
        {"title": "Answer/Demurrer due", "days": 30, "type": "filing", "source": "CCP §412.20(a)(3)", "priority": "high"},
        {"title": "Case Management Conference", "days": 180, "type": "hearing", "source": "CRC 3.722", "priority": "normal"},
        {"title": "Propound Form Interrogatories", "days": 10, "type": "discovery", "source": "CCP §2030.020", "priority": "high"},
        {"title": "Propound Special Interrogatories", "days": 10, "type": "discovery", "source": "CCP §2030.020", "priority": "high"},
        {"title": "Propound RFPs", "days": 10, "type": "discovery", "source": "CCP §2031.020", "priority": "high"},
        {"title": "Propound RFAs", "days": 10, "type": "discovery", "source": "CCP §2033.020", "priority": "normal"},
    ],
    "answer_filed": [
        {"title": "Discovery cutoff (C-30)", "days": -30, "type": "discovery", "source": "CCP §2024.020", "priority": "critical", "from_trial": True},
        {"title": "Expert discovery cutoff (C-15)", "days": -15, "type": "discovery", "source": "CCP §2024.030", "priority": "critical", "from_trial": True},
        {"title": "MSJ filing deadline (C-81)", "days": -81, "type": "filing", "source": "CCP §437c(a) (AB 2049)", "priority": "high", "from_trial": True},
        {"title": "Expert demand deadline (C-70)", "days": -70, "type": "discovery", "source": "CCP §2034.220", "priority": "high", "from_trial": True},
        {"title": "Expert disclosure deadline (C-50)", "days": -50, "type": "discovery", "source": "CCP §2034.230", "priority": "high", "from_trial": True},
        {"title": "Last day to serve written discovery (C-100)", "days": -100, "type": "discovery", "source": "CCP §§2024.020, 2030.260", "priority": "high", "from_trial": True},
    ],
    "discovery_served": [
        {"title": "Discovery response due", "days": 30, "type": "discovery", "source": "CCP §2030.260", "priority": "high"},
        {"title": "Motion to compel deadline", "days": 45, "type": "filing", "source": "CCP §2030.300", "priority": "normal", "from_response_due": True},
    ],
    "trial_set": [
        {"title": "Trial", "days": 0, "type": "trial", "priority": "critical"},
        {"title": "Final Status Conference", "days": -10, "type": "hearing", "source": "Local rule", "priority": "high"},
        {"title": "Motions in Limine due", "days": -15, "type": "filing", "source": "Local rule", "priority": "high"},
        {"title": "Exchange exhibit lists", "days": -15, "type": "filing", "source": "CRC 3.1550", "priority": "high"},
        {"title": "Exchange witness lists", "days": -15, "type": "filing", "source": "CRC 3.1550", "priority": "high"},
        {"title": "Trial briefs due", "days": -10, "type": "filing", "source": "Local rule", "priority": "high"},
        {"title": "Jury instructions due", "days": -10, "type": "filing", "source": "CRC 2.1055", "priority": "high"},
        {"title": "Discovery cutoff", "days": -30, "type": "discovery", "source": "CCP §2024.020", "priority": "critical"},
        {"title": "Expert discovery cutoff", "days": -15, "type": "discovery", "source": "CCP §2024.030", "priority": "critical"},
        {"title": "MSJ hearing deadline", "days": -30, "type": "hearing", "source": "CCP §437c (AB 2049)", "priority": "high"},
        {"title": "MSJ filing deadline (81-day notice)", "days": -81, "type": "filing", "source": "CCP §437c(a) (AB 2049)", "priority": "high"},
        {"title": "Expert demand deadline", "days": -70, "type": "discovery", "source": "CCP §2034.220", "priority": "high"},
        {"title": "Expert disclosure deadline", "days": -50, "type": "discovery", "source": "CCP §2034.230", "priority": "high"},
    ],
}


class CalendarEngine:
    """Computes and manages litigation deadlines."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    def compute_deadlines(
        self,
        trigger_event: str,
        event_date: date | str,
        case_id: str | None = None,
        org_id: str | None = None,
        trial_date: date | str | None = None,
        service_method: str = "electronic",
    ) -> list[dict]:
        """
        Compute all deadlines triggered by an event.

        Args:
            trigger_event: complaint_filed, answer_filed, discovery_served, trial_set
            event_date: when the triggering event occurred
            trial_date: trial date (needed for trial-relative deadlines)
            service_method: how papers were served (affects extensions)
        """
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        if isinstance(trial_date, str):
            trial_date = date.fromisoformat(trial_date)

        templates = LITIGATION_DEADLINES.get(trigger_event, [])
        extension = SERVICE_EXTENSIONS.get(service_method, 0)
        deadlines = []

        for tmpl in templates:
            if tmpl.get("from_trial") and trial_date:
                deadline_date = trial_date + timedelta(days=tmpl["days"])
            elif tmpl.get("from_response_due"):
                response_due = event_date + timedelta(days=30 + extension)
                deadline_date = response_due + timedelta(days=tmpl["days"])
            else:
                deadline_date = event_date + timedelta(days=tmpl["days"] + extension)

            dl = {
                "title": tmpl["title"],
                "deadline_date": deadline_date.isoformat(),
                "deadline_type": tmpl["type"],
                "source": tmpl.get("source", ""),
                "priority": tmpl.get("priority", "normal"),
                "auto_generated": True,
                "reminder_days": [7, 3, 1],
            }
            if case_id:
                dl["case_id"] = case_id
            if org_id:
                dl["org_id"] = org_id

            deadlines.append(dl)

        # Save to database
        if self.db and case_id:
            for dl in deadlines:
                self.db.table("case_deadlines").insert(dl).execute()

            # Also add timeline events
            for dl in deadlines:
                self.db.table("case_timeline").insert({
                    "case_id": case_id,
                    "org_id": org_id,
                    "event_date": dl["deadline_date"],
                    "title": dl["title"],
                    "event_type": dl["deadline_type"],
                    "auto_generated": True,
                }).execute()

        return deadlines

    def get_upcoming_deadlines(
        self,
        org_id: str,
        days_ahead: int = 30,
        case_id: str | None = None,
    ) -> list[dict]:
        """Get upcoming deadlines within the specified window."""
        if not self.db:
            return []

        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        query = (
            self.db.table("case_deadlines")
            .select("*, cases(case_name)")
            .eq("org_id", org_id)
            .eq("completed", False)
            .gte("deadline_date", today.isoformat())
            .lte("deadline_date", end_date.isoformat())
            .order("deadline_date")
        )

        if case_id:
            query = query.eq("case_id", case_id)

        result = query.execute()
        deadlines = result.data or []

        # Add urgency classification
        for dl in deadlines:
            dl_date = date.fromisoformat(dl["deadline_date"])
            days_until = (dl_date - today).days
            if days_until <= 1:
                dl["urgency"] = "critical"
                dl["urgency_color"] = "#dc3545"
            elif days_until <= 3:
                dl["urgency"] = "urgent"
                dl["urgency_color"] = "#fd7e14"
            elif days_until <= 7:
                dl["urgency"] = "soon"
                dl["urgency_color"] = "#ffc107"
            else:
                dl["urgency"] = "normal"
                dl["urgency_color"] = "#28a745"

        return deadlines

    def get_case_timeline(self, case_id: str) -> list[dict]:
        """Get the full timeline for a case."""
        if not self.db:
            return []

        result = (
            self.db.table("case_timeline")
            .select("*")
            .eq("case_id", case_id)
            .order("event_date")
            .execute()
        )
        return result.data or []

    def complete_deadline(self, deadline_id: str) -> dict:
        """Mark a deadline as completed."""
        if not self.db:
            return {"error": "Database not available"}

        from datetime import datetime, timezone
        result = self.db.table("case_deadlines").update({
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", deadline_id).execute()

        return result.data[0] if result.data else {"error": "Deadline not found"}
