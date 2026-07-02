# Priority Remediation Plan

**Client:** {{Client Company}} · **Date:** {{Date}}

> GUIDANCE: The sequenced to-do list the client actually executes: what to
> fix first, what can wait, and what needs a leadership decision. Every item
> traces to a finding ID (P-x, B-x, gap #, VTA-x) and lands in one of three
> buckets. Resist the urge to mark everything "now" — a plan where
> everything is urgent gives the client no plan at all.

## How to read this

- **Fix now (≤30 days):** live exposure or trivial effort. Do these before
  anything else.
- **Scheduled (30–120 days):** matters, but sequenced behind the "now"
  items or dependent on them.
- **Leadership decision required:** not a task — a position the business
  must take. Anchor frames the options; the client decides.

## 1. Fix now

| # | Action | Fixes | Owner | Effort | Done when |
|---|---|---|---|---|---|
| N-1 | {{Migrate the {{N}} heaviest AI users to company accounts with training-off terms}} | P-1 / Confid. {{score}} | {{IT}} | {{2 days}} | {{Survey tools show zero work logins on personal accounts for those users}} |
| N-2 | {{Turn off default-on meeting AI for external calls pending counsel review}} | P-2 / AI-03 | {{Owner}} | {{1 hour}} | {{Setting confirmed org-wide}} |
| N-3 | {{Add human approval step to lead-reply automation}} | B-1 risk / AI-04 | {{Marketing lead}} | {{Half day}} | {{No message sends without click-approve}} |
| N-4 | {{Publish data traffic-light one-pager}} | P-1, Gap 2 | {{Owner}} | {{1 day}} | {{Posted + linked in onboarding}} |

## 2. Scheduled

| # | Action | Fixes | Target | Depends on |
|---|---|---|---|---|
| S-1 | {{Adopt AI Acceptable Use Policy}} | Gaps 1–3, 5, 8 | Day {{45}} | Counsel review |
| S-2 | {{All-hands training + acknowledgment}} | Gap 9 | Day {{60}} | S-1 |
| S-3 | {{Sign DPA with {{vendor}}; upgrade {{tool}} tier}} | VTA-{{x}} | Day {{60}} | Budget approval |
| S-4 | {{Quarterly review #1 (inventory + re-score)}} | Reg. readiness | Day {{100}} | S-1–S-3 |

## 3. Leadership decisions required

| # | Decision | Options framed | Informed by | Needed by |
|---|---|---|---|---|
| D-1 | {{Client disclosure position: disclose AI-assisted work proactively, on request, or not at all?}} | {{pros/cons one-liner each}} | Gap 4; {{industry norms}} | {{Day 45 — blocks S-1 final text}} |
| D-2 | {{Keep or kill resume-screening AI feature?}} | {{Disable / keep with counsel-designed process}} | Empl. flag; counsel input | {{Day 30}} |
| D-3 | {{Retainer vs. self-run quarterly reviews}} | {{...}} | Roadmap Phase 3 | {{Day 90}} |

## 4. Explicitly deferred

Items reviewed and consciously *not* scheduled — so the client knows they
were considered, not missed:

- {{e.g., "CRM re-keying automation (B-2): real but small; bundle into any
  Build engagement rather than standalone."}}
- {{e.g., "ISO/SOC certification for the client itself: premature at this
  headcount."}}

## 5. Counsel review queue

Factual records ready to hand to qualified counsel:

| Item | Record | Question for counsel |
|---|---|---|
| P-1 | Privacy review §2, §4 | {{Do client confidentiality clauses reach AI vendor processing?}} |
| P-2 | Privacy review §2; VTA-02 | {{Recording-consent requirements for meeting AI on client calls}} |
| Empl. | Scorecard employment row | {{Obligations triggered by ATS screening feature}} |

## 6. Tracking

Review this plan at the {{Day 30}} check-in and at each quarterly review.
Completed items move to a log with date + evidence; the executive report's
next edition opens with the delta.
