# Risk & Opportunity Scorecard

**Client:** {{Client Company}} · **Date:** {{Date}} · **Scope:** {{teams/systems}}

> GUIDANCE: This is the audit's quantitative spine. Score each dimension
> from evidence (survey stats, inventory entries, documents) and cite that
> evidence in the rationale column — a score without evidence is an opinion.
> Use the same 1–5 scale in every other deliverable.

## Rating scale

**Risk (per dimension):**
- **1 — Managed:** documented controls, followed in practice
- **2 — Adequate:** controls exist; gaps are minor or well-understood
- **3 — Developing:** partial/informal controls; relies on individual judgment
- **4 — Exposed:** no effective control over a live, material exposure
- **5 — Critical:** active exposure with evidence of realized or imminent harm

**Opportunity:** sized as estimated hours/week recoverable × affected
headcount, rated Low (<5 h/wk team-wide), Medium (5–20), High (20+).

## A. Risk scorecard

| Dimension | Score | Trend | Evidence & rationale |
|---|---|---|---|
| **Confidentiality** — company/client data reaching AI systems without controls | {{1–5}} | {{↑→↓}} | {{e.g., "Survey: 8 respondents entered client details into AI tools; 40% personal-account use (AI-02); no DLP or account policy."}} |
| **Accuracy & reliance** — unverified AI output reaching decisions or clients | {{1–5}} | | {{e.g., "Survey: 22% 'rarely/never' verify output; one shipped error reported (Q12); no review step in AI-04 automation."}} |
| **Vendor** — dependence on AI vendors' terms, security, and continuity | {{1–5}} | | {{Cite vendor assessment: training-on-data defaults, missing DPAs, auto-enabled features (AI-03).}} |
| **Employment** — AI use in hiring/evaluation; monitoring; role impact handling | {{1–5}} | | {{e.g., "Resume screening feature enabled in ATS — automated employment decisions may trigger specific legal obligations; flag for counsel."}} |
| **Intellectual property** — ownership/provenance of AI-assisted work product; company IP leaving via prompts | {{1–5}} | | {{e.g., "Source code pasted into personal accounts (survey Q10); client deliverables include AI-generated content with no disclosure position."}} |
| **Regulatory readiness** — ability to answer "what AI do you use, on what data, with what oversight?" | {{1–5}} | | {{e.g., "Before this audit: no inventory, no policy, no designated owner. This document set is the starting record."}} |

**Composite risk: {{X.X}} / 5** (unweighted mean unless client context
justifies weighting — if weighted, state the weights).

> Items scored 4–5 in dimensions with legal significance (confidentiality,
> employment, IP, regulatory) are flagged for review by qualified counsel in
> the remediation plan.

## B. Opportunity scorecard

| # | Opportunity | Where | Size | Effort | Rationale |
|---|---|---|---|---|---|
| O-1 | {{e.g., Document intake summarization}} | {{Team}} | {{H/M/L + est. h/wk}} | {{L/M/H}} | {{Survey Q8/Q9 signals, interview evidence}} |
| O-2 | {{...}} | | | | |
| O-3 | {{...}} | | | | |

## C. The grid

Plot risks (R#) and opportunities (O#) — this becomes the executive report's
one-slide summary:

```
 impact ↑   | act now        | plan deliberately
            | (high/low)     | (high/high)
            |----------------+------------------
            | monitor        | quick wins
            | (low/low)      | (low/high... invert for opportunities)
            +--------------------------------→ effort to address
```

**Act now:** {{items}} · **Quick wins:** {{items}} · **Plan:** {{items}} ·
**Monitor:** {{items}}

## D. Re-scoring

Re-score at each quarterly review (see inventory tracking system). Record
history here:

| Date | Conf. | Acc. | Vendor | Empl. | IP | Reg. | Composite |
|---|---|---|---|---|---|---|---|
| {{audit date}} | | | | | | | |
