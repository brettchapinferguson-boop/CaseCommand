"""Tests for the California deadline rules engine."""
from datetime import date

import pytest
import rules


def test_weekend_rolls_forward():
    # 2026-07-03 (Fri, but July 4 observed) + 1 day = Sat 7/4 → rolls to Mon 7/6
    result = rules.add_calendar_days(date(2026, 7, 3), 1)
    assert result == date(2026, 7, 6)


def test_holiday_rolls_forward():
    # Landing on Christmas 2026 (Fri) rolls to Mon 12/28
    result = rules.add_calendar_days(date(2026, 12, 24), 1)
    assert result == date(2026, 12, 28)


def test_plain_weekday_no_roll():
    # Wed + 1 = Thu, no roll
    assert rules.add_calendar_days(date(2026, 7, 1), 1) == date(2026, 7, 2)


def test_court_days_skip_weekend():
    # Thu 2026-07-02 + 2 court days: Fri 7/3 is a court day? July 4 2026 is
    # Saturday → observed Friday 7/3. So next court days are Mon 7/6, Tue 7/7.
    result = rules.add_court_days(date(2026, 7, 2), 2)
    assert result == date(2026, 7, 7)


def test_backward_rolls_to_prev_court_day():
    # Counting backward onto Sunday rolls back to Friday
    result = rules.add_calendar_days(date(2026, 7, 7), -2)  # Sun 7/5
    assert result.weekday() < 5


def test_mail_service_extension():
    base = date(2026, 7, 1)
    extended = rules.apply_service_extension(base, "mail")
    assert (extended - base).days >= 5


def test_personal_service_no_extension():
    base = date(2026, 7, 1)
    assert rules.apply_service_extension(base, "personal") == base


def test_electronic_service_court_days():
    # Fri 2026-07-10 + 2 court days = Tue 7/14
    extended = rules.apply_service_extension(date(2026, 7, 10), "electronic")
    assert extended == date(2026, 7, 14)


def test_compute_discovery_response_deadline():
    result = rules.compute_deadlines(
        "discovery_propounded", date(2026, 7, 1), "mail"
    )
    assert len(result) == 1
    # 30 days + 5 mail = 35 days → 2026-08-05 (Wednesday)
    assert result[0]["due_date"] == "2026-08-05"
    assert "2030.260" in result[0]["rule"]


def test_compute_motion_to_compel_jurisdictional():
    result = rules.compute_deadlines(
        "discovery_responses_received", date(2026, 7, 1), "personal"
    )
    assert len(result) == 1
    # 45 days from 7/1 → 8/15 (Saturday) → rolls to Mon 8/17
    assert result[0]["due_date"] == "2026-08-17"
    assert "JURISDICTIONAL" in result[0]["title"]


def test_compute_incident_deadlines():
    result = rules.compute_deadlines("incident", date(2026, 1, 15))
    titles = [r["title"] for r in result]
    assert any("Statute of limitations" in t for t in titles)
    assert any("Government tort claim" in t for t in titles)
    sol = next(r for r in result if "Statute" in r["title"])
    assert sol["due_date"].startswith("2028-01")


def test_compute_trial_deadlines_count_backward():
    result = rules.compute_deadlines("trial_date_set", date(2026, 12, 7))
    # All trial-anchored deadlines come before trial
    for r in result:
        assert r["due_date"] < "2026-12-07"
    titles = " ".join(r["title"] for r in result)
    assert "summary judgment" in titles
    assert "discovery cutoff" in titles.lower()
    assert "998" in titles


def test_unknown_trigger_raises():
    with pytest.raises(ValueError):
        rules.compute_deadlines("bogus_event", date(2026, 7, 1))


def test_every_result_has_verification_flag():
    result = rules.compute_deadlines("trial_date_set", date(2026, 12, 7))
    for r in result:
        assert "verify" in r
        assert "attorney" in r["verify"].lower()


def test_holidays_include_major_dates():
    hols = rules.california_court_holidays(2026)
    assert date(2026, 1, 1) in hols
    assert date(2026, 11, 26) in hols  # Thanksgiving
    assert date(2026, 12, 25) in hols
