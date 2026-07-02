"""
CaseCommand — California Litigation Deadline Rules Engine
==========================================================
Computes litigation deadlines from trigger events under the California
Code of Civil Procedure, California Rules of Court, and Government Code.

IMPORTANT: These computations are drafting aids. Every computed deadline
is flagged for attorney verification. Local rules, court orders, and
case-specific facts can change any deadline.

Covers:
- Calendar-day and court-day arithmetic (CCP §§12, 12a, 12c)
- Weekend/holiday roll-forward and roll-backward
- Service-method extensions (CCP §1013, §1010.6)
- Common trigger events: incident, complaint filed/served, discovery
  propounded/received, trial date set
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

# ── Service extensions (CCP §1013, §1010.6(a)(3)(B)) ──
# value: (days, "calendar" | "court")
SERVICE_EXTENSIONS = {
    "personal": (0, "calendar"),
    "mail": (5, "calendar"),        # CCP §1013(a) — within California
    "overnight": (2, "calendar"),   # CCP §1013(c) — Express Mail / overnight
    "electronic": (2, "court"),     # CCP §1010.6(a)(3)(B)
}


# ── California court holidays ─────────────────────
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """nth occurrence of weekday (0=Mon) in month. n=-1 for last."""
    if n > 0:
        d = date(year, month, 1)
        offset = (weekday - d.weekday()) % 7
        return d + timedelta(days=offset + 7 * (n - 1))
    # last occurrence
    d = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    offset = (d.weekday() - weekday) % 7
    return d - timedelta(days=offset)


def _observed(d: date) -> date:
    """Holiday falling on Sat is observed Fri; Sun observed Mon (Gov C §6700 et seq.)."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def california_court_holidays(year: int) -> set:
    """Judicial holidays for California courts (Gov. Code §6700; CRC 1.11).

    Approximation covering the statewide set. Verify against the specific
    court's calendar for local closures.
    """
    holidays = {
        _observed(date(year, 1, 1)),                    # New Year's Day
        _nth_weekday(year, 1, 0, 3),                    # MLK Day (3rd Mon Jan)
        date(year, 2, 12) if date(year, 2, 12).weekday() < 5 else _observed(date(year, 2, 12)),  # Lincoln's Birthday
        _nth_weekday(year, 2, 0, 3),                    # Presidents' Day (3rd Mon Feb)
        _observed(date(year, 3, 31)),                   # Cesar Chavez Day
        _nth_weekday(year, 5, 0, -1),                   # Memorial Day (last Mon May)
        _observed(date(year, 6, 19)),                   # Juneteenth
        _observed(date(year, 7, 4)),                    # Independence Day
        _nth_weekday(year, 9, 0, 1),                    # Labor Day (1st Mon Sep)
        _observed(date(year, 9, 9)),                    # Admission Day (courts)
        _nth_weekday(year, 10, 0, 2),                   # Indigenous Peoples'/Columbus Day
        _observed(date(year, 11, 11)),                  # Veterans Day
        _nth_weekday(year, 11, 3, 4),                   # Thanksgiving (4th Thu Nov)
        _nth_weekday(year, 11, 3, 4) + timedelta(days=1),  # Day after Thanksgiving
        _observed(date(year, 12, 25)),                  # Christmas
    }
    return holidays


def is_court_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in california_court_holidays(d.year)


def next_court_day(d: date) -> date:
    """Roll forward to the next court day (CCP §12a)."""
    while not is_court_day(d):
        d += timedelta(days=1)
    return d


def prev_court_day(d: date) -> date:
    """Roll backward to the previous court day (CCP §12c for hearing-anchored deadlines)."""
    while not is_court_day(d):
        d -= timedelta(days=1)
    return d


def add_calendar_days(start: date, days: int) -> date:
    """Add calendar days; if the result lands on a weekend/holiday, roll
    forward (CCP §§12, 12a) for forward deadlines, backward for
    reverse-computed (before-event) deadlines."""
    result = start + timedelta(days=days)
    if days >= 0:
        return next_court_day(result)
    return prev_court_day(result)


def add_court_days(start: date, days: int) -> date:
    """Add court days, skipping weekends and holidays."""
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    d = start
    while remaining > 0:
        d += timedelta(days=step)
        if is_court_day(d):
            remaining -= 1
    return d


def apply_service_extension(deadline: date, service_method: str) -> date:
    """Extend a responsive deadline for the method of service (CCP §1013, §1010.6)."""
    days, kind = SERVICE_EXTENSIONS.get(service_method, (0, "calendar"))
    if days == 0:
        return deadline
    if kind == "court":
        return add_court_days(deadline, days)
    return add_calendar_days(deadline, days)


# ── Deadline rules by trigger event ───────────────
# Each rule: (title, statute, days, day_type, extend_for_service)
# Negative days = counted backward from the anchor (e.g., trial date).
DEADLINE_RULES: Dict[str, List[Dict]] = {
    "incident": [
        {"title": "Statute of limitations — personal injury (2 years)",
         "rule": "CCP §335.1", "days": 730, "day_type": "calendar", "service_ext": False},
        {"title": "Government tort claim deadline (6 months)",
         "rule": "Gov. Code §911.2", "days": 180, "day_type": "calendar", "service_ext": False,
         "note": "Only if a public entity is a defendant"},
    ],
    "complaint_filed": [
        {"title": "Serve complaint and file proof of service",
         "rule": "CRC 3.110(b)", "days": 60, "day_type": "calendar", "service_ext": False},
    ],
    "complaint_served": [
        {"title": "Defendant's responsive pleading due",
         "rule": "CCP §412.20(a)(3)", "days": 30, "day_type": "calendar", "service_ext": False},
    ],
    "discovery_propounded": [
        {"title": "Responses to written discovery due",
         "rule": "CCP §§2030.260(a), 2031.260(a), 2033.250(a)", "days": 30,
         "day_type": "calendar", "service_ext": True},
    ],
    "discovery_responses_received": [
        {"title": "Motion to compel further responses — JURISDICTIONAL",
         "rule": "CCP §§2030.300(c), 2031.310(c), 2033.290(c)", "days": 45,
         "day_type": "calendar", "service_ext": True,
         "note": "45-day limit is jurisdictional; may be extended only by written agreement"},
    ],
    "trial_date_set": [
        {"title": "Last day to file motion for summary judgment (heard 30 days before trial; 81-day notice)",
         "rule": "CCP §437c(a)(2)-(3)", "days": -111, "day_type": "calendar", "service_ext": False,
         "note": "Approximate; verify hearing availability and add service-method notice extensions"},
        {"title": "Demand for exchange of expert witness information",
         "rule": "CCP §2034.220", "days": -70, "day_type": "calendar", "service_ext": False,
         "note": "No later than the 10th day after initial trial date is set, or 70 days before trial, whichever is closer to trial"},
        {"title": "Expert witness exchange",
         "rule": "CCP §2034.230(b)", "days": -50, "day_type": "calendar", "service_ext": False},
        {"title": "Non-expert discovery cutoff",
         "rule": "CCP §2024.020(a)", "days": -30, "day_type": "calendar", "service_ext": False},
        {"title": "Expert discovery cutoff",
         "rule": "CCP §2024.030", "days": -15, "day_type": "calendar", "service_ext": False},
        {"title": "Discovery motion cutoff",
         "rule": "CCP §2024.020(a)", "days": -15, "day_type": "calendar", "service_ext": False},
        {"title": "Last day to serve CCP §998 offer",
         "rule": "CCP §998(b)", "days": -10, "day_type": "calendar", "service_ext": False},
    ],
}

TRIGGER_EVENTS = sorted(DEADLINE_RULES.keys())


def compute_deadlines(
    trigger_event: str,
    event_date: date,
    service_method: str = "personal",
) -> List[Dict]:
    """Compute all deadlines flowing from a trigger event.

    Returns a list of {title, rule, due_date (ISO), note} dicts.
    Raises ValueError for unknown trigger events.
    """
    if trigger_event not in DEADLINE_RULES:
        raise ValueError(
            f"Unknown trigger event '{trigger_event}'. "
            f"Known events: {', '.join(TRIGGER_EVENTS)}"
        )

    results = []
    for r in DEADLINE_RULES[trigger_event]:
        # Compute the raw period (including any service extension) first,
        # then roll off weekends/holidays once at the end (CCP §§12, 12a).
        if r["day_type"] == "court":
            raw = add_court_days(event_date, r["days"])
        else:
            raw = event_date + timedelta(days=r["days"])
        if r.get("service_ext"):
            ext_days, kind = SERVICE_EXTENSIONS.get(service_method, (0, "calendar"))
            if kind == "court":
                raw = add_court_days(raw, ext_days)
            else:
                raw += timedelta(days=ext_days)
        due = next_court_day(raw) if r["days"] >= 0 else prev_court_day(raw)
        entry = {
            "title": r["title"],
            "rule": r["rule"],
            "due_date": due.isoformat(),
            "note": r.get("note", ""),
            "verify": "Computed deadline — attorney must verify against local rules and court orders",
        }
        results.append(entry)
    return results
