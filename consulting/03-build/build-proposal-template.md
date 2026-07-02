# Anchor Build Proposal

**Client:** {{Client Company}} · **Date:** {{Date}}
**Builds on:** {{Anchor Audit dated X / Discovery Snapshot dated X}}

> GUIDANCE: The bridge from audit findings to a signed Build SOW. Scope ONE
> primary build (the top opportunity), not a program — ship something
> working in weeks, earn the next build. Reference finding IDs so the
> proposal reads as the audit's logical consequence, and let the audit's
> governance work show up in the build's guardrails: that is Anchor's
> differentiator.

## 1. What the audit found

{{Two sentences: "The audit identified O-1 (intake summarization, est.
10 h/wk) as the highest-value, lowest-risk build candidate, with B-1's
queue delay costing response time on every inbound lead. This proposal
scopes that build."}}

## 2. What we'll build

**Working name:** {{e.g., "Intake Assist"}}

{{Plain-English description, 3–5 sentences: what it does, who uses it, what
changes about their day. No architecture yet.}}

**Explicitly in scope:** {{bulleted capabilities}}
**Explicitly out of scope:** {{what it will NOT do — as important}}

## 3. How it fits the governance model

The build inherits the guardrails from the audit:

- **Human checkpoint:** {{where a person approves output before it acts —
  per remediation N-3 pattern}}
- **Data rules:** {{which data classes it touches, per the traffic-light
  table; which vendor/model per the approved list, e.g., "Claude via API
  under the reviewed enterprise terms (VTA-01)"}}
- **Inventory entry:** registered as AI-{{xx}} with a named owner on day one
- **Failure posture:** {{what happens when it's wrong or down — fallback to
  the manual process}}

## 4. Delivery plan

| Week | Milestone | You'll see |
|---|---|---|
| 1 | Design sprint: workflow walkthrough, prompt/data design, success criteria agreed | Design doc + acceptance criteria |
| 2–3 | Working prototype on real (redacted) examples | Demo with your data; feedback round |
| 4 | Iteration with {{using team}}; edge cases; checkpoint UX | v1 candidate in your environment |
| 5 | Deploy, train the team ({{60-min}} session), document | Live system + runbook + training |
| +30 days | Tune-up: review logs, fix drift, measure | Usage & accuracy report vs. baseline |

## 5. Success criteria (measured, not vibes)

| Metric | Baseline (from audit) | Target |
|---|---|---|
| {{e.g., Time from inquiry → first response}} | {{2 days median}} | {{<4 business hours}} |
| {{Hours/week on manual step}} | {{10 h/wk}} | {{≤3 h/wk}} |
| {{Human-checkpoint override rate}} | — | {{<20% by day 30, trending down}} |

Acceptance is defined per criterion in the SOW; the +30-day tune-up
measures them against baseline.

## 6. What we need from you

- {{Using team}}: {{~2 hrs}} in week 1, {{~1 hr/wk}} feedback thereafter
- Access: {{systems, sample data (redacted per data rules)}}
- A decision-maker for the weekly demo

## 7. Investment

**{{Fixed fee $X}}**, covering design through the +30-day tune-up.
{{Payment schedule.}} Ongoing support options: {{monthly retainer $X —
monitoring, iteration, quarterly re-audit alignment / as-needed at $X/hr}}.

## 8. After this build

{{One paragraph: the natural next candidates from the audit (O-2, B-2
integration work) — noted for roadmap honesty, not scoped here.}}

**To proceed:** sign the attached Build SOW; week 1 starts {{date}}.
