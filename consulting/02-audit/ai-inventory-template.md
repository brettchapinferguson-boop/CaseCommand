# AI Tool, Agent & Automation Inventory

**Client:** {{Client Company}} · **As of:** {{Date}} · **Compiled by:** Anchor AI Solutions

> GUIDANCE: This is the audit's factual backbone — every other deliverable
> cites entries here by ID. Sources: employee survey, interviews, SSO/billing
> review, browser-extension check, vendor list. An entry belongs here if it
> makes automated decisions, generates content, or moves company data —
> including AI *features inside* existing SaaS, which clients always miss.

## A. Inventory

| ID | Name | Category | Used by | Account type | Sanctioned? | Data it touches | Runs unattended? | Vendor assessed? |
|---|---|---|---|---|---|---|---|---|
| AI-01 | {{ChatGPT Team}} | Chat assistant | {{Ops, ~12 users}} | Company | Yes | {{Internal docs, some client names}} | No | → VTA-01 |
| AI-02 | {{Personal ChatGPT accounts}} | Chat assistant | {{~40% of staff (survey)}} | Personal | No | {{Unknown — survey indicates client data}} | No | N/A |
| AI-03 | {{Zoom AI Companion}} | Embedded feature | {{All meetings}} | Company | Default-on | {{Meeting audio incl. client calls}} | Yes (auto-summary) | → VTA-02 |
| AI-04 | {{Zapier flow: lead intake}} | Automation/agent | {{Marketing}} | Company | Yes | {{Prospect PII}} | **Yes** | → VTA-03 |

**Categories:** chat assistant · embedded SaaS feature · coding assistant ·
transcription · image/media · automation/agent · custom/internal ·
API usage in product.

## B. Shadow usage summary

{{From survey aggregates: e.g., "Survey indicates 40% of respondents use
personal AI accounts for work; 8 respondents report having entered client
details into an AI tool. Individual identities unknown by design."}}

## C. Unattended systems register

Anything that acts without a human reviewing each output — highest scrutiny.

| ID | What it does autonomously | Failure mode | Human checkpoint? | Owner |
|---|---|---|---|---|
| AI-04 | {{Sends templated replies to inbound leads}} | {{Wrong/odd reply to a prospect}} | {{None today}} | {{Name}} |

## D. Ongoing Tracking System

The inventory decays in ~90 days without a process. Anchor recommends and
sets up the following with the client:

1. **Owner.** One named person ({{role}}) owns the inventory.
2. **Intake gate.** A lightweight request form (tool, purpose, data
   involved) — the goal is a 48-hour default-yes for low-risk tools, so the
   gate is easier than going around it.
3. **Quarterly refresh (30 min).** Re-pull SSO/billing app list; diff
   against inventory; ask each dept head one question: "anything new?"
4. **Vendor-change watch.** When a SaaS vendor announces AI features, the
   owner adds a row and checks default settings (see AI-03 for why).
5. **Annual survey re-run.** Repeat the anonymous survey annually; compare
   personal-account and data-exposure rates year over year.

**Handoff checklist:** ☐ Owner named ☐ Intake form live ☐ Calendar holds for
quarterly refresh ☐ This document transferred to client's system of record.
