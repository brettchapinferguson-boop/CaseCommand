# Build Acceptance & Handoff Checklist

**Build:** {{name}} · **Client:** {{Client Company}} · **Handoff date:** {{Date}}

> GUIDANCE: Closes out a Build engagement cleanly. Nothing here should be a
> surprise — acceptance criteria came from the proposal/SOW, and governance
> items mirror the client's own roadmap. Walk this document WITH the client
> in the final session; both parties initial each section.

## 1. Acceptance criteria

From SOW §{{x}} — measured, with evidence attached:

| # | Criterion | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | {{Response time}} | {{<4 bus. hrs}} | {{...}} | ☐ |
| 2 | {{Hours recovered}} | {{≤3 h/wk manual}} | {{...}} | ☐ |
| 3 | {{Override rate}} | {{<20%}} | {{...}} | ☐ |

**Open punch-list items (with owner + date):** {{list or "none"}}

## 2. Deployment

- ☐ Running in client environment: {{where — client's cloud account,
  client-owned subscriptions}}
- ☐ All credentials/API keys owned and held by client (Anchor access
  revoked or converted to support-only per §6)
- ☐ Vendor accounts on reviewed terms ({{VTA-xx}}); billing transferred
- ☐ Monitoring/alerting live; alerts route to {{client role}}
- ☐ Rollback tested: manual process still works if the system is off

## 3. Documentation delivered

- ☐ **Runbook** — start/stop, common failures, who to call
- ☐ **Prompt & configuration reference** — what's tunable and what isn't
- ☐ **Architecture one-pager** — components, data flow, vendor dependencies
- ☐ **Change log** — versioned record of what shipped

## 4. Training

- ☐ Using team trained ({{date}}, {{N}} attendees, recording shared)
- ☐ System owner trained on runbook + checkpoint queue
- ☐ "What to do when it's wrong" covered explicitly (override, report,
  fallback — ties to the incident channel from the governance roadmap)

## 5. Governance integration

- ☐ Registered in AI inventory as AI-{{xx}} with named owner
- ☐ Human checkpoint verified operating as designed (per proposal §3)
- ☐ Data flows match the traffic-light rules; no new data classes without
  re-review
- ☐ Added to quarterly review scope (re-score at next cycle)
- ☐ If client-facing: disclosure position (D-{{x}}) applied

## 6. Support terms from here

- **Warranty:** defects in delivered scope fixed at no charge for
  {{30/60}} days from acceptance
- **Ongoing:** {{retainer terms / as-needed rate / none — client
  self-supports per runbook}}
- **Escalation contact:** {{name, channel, response expectation}}
- **+30-day tune-up scheduled:** {{date}}

## 7. Sign-off

The build described in SOW #{{YYYY-NN}} is accepted {{in full / with the
punch list in §1}}.

**{{Client Company}}:** ______________________ Date: ________

**Anchor AI Solutions:** ______________________ Date: ________
