# Anchor AI Solutions — Consulting Deliverables Library

This directory contains the working templates behind every Anchor engagement.
Each file is a client-ready Markdown template: duplicate it into the client's
engagement folder, replace the `{{placeholders}}`, and delete any guidance
blocks (marked `> GUIDANCE:`) before delivery.

Templates map one-to-one to what the landing page promises.

## Structure

| Folder | Package | Contents |
|---|---|---|
| `00-engagement/` | All | Engagement letter, statement of work |
| `01-discovery/` | Discovery Engagement | Leadership intake guide, snapshot findings report |
| `02-audit/` | Anchor Audit | The ten audit deliverables (survey, inventory, scorecard, privacy review, vendor assessment, policy gap analysis, workflow map, governance roadmap, remediation plan, executive report) |
| `03-build/` | Anchor Build | Build proposal, acceptance & handoff checklist |

## Engagement flow

1. **Discovery call → Engagement letter + SOW** (`00-engagement/`)
2. **Discovery Engagement** (`01-discovery/`) — intake interview, light tool
   review, snapshot report with a recommended next scope.
3. **Anchor Audit** (`02-audit/`) — run the survey and inventory first; they
   feed the scorecard, privacy review, and vendor assessment, which feed the
   gap analysis, roadmap, and remediation plan; everything rolls up into the
   executive report.
4. **Anchor Build** (`03-build/`) — proposal scoped from audit findings,
   closed out with the acceptance & handoff checklist.

## Conventions

- `{{Client}}`, `{{Date}}`, `{{Consultant}}` etc. are fill-in placeholders.
- Risk ratings use a consistent 1–5 scale defined in
  `02-audit/risk-opportunity-scorecard.md`. Use the same scale everywhere.
- Deliverables are consulting work product, **not legal advice**. Where a
  finding has legal implications, the template language routes the client to
  qualified counsel.
- Final client copies are typically exported to .docx/PDF with Anchor
  branding; these Markdown files are the canonical source.
