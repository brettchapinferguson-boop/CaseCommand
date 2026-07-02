# Data Privacy Review

**Client:** {{Client Company}} · **Date:** {{Date}} · **Reviewer:** {{Consultant}}

> GUIDANCE: This maps what data flows into AI systems against the promises
> the client has made about that data (contracts, privacy policy, law). It
> is a consulting review, not a legal compliance opinion — where a flow may
> breach an obligation, the deliverable's job is to surface it clearly and
> route it to counsel.

## 1. Data categories in play

| Category | Examples at this client | Sensitivity |
|---|---|---|
| Client/customer PII | {{names, contact info, account details}} | High |
| Client confidential business data | {{deal terms, case files, financials}} | High |
| Employee/HR data | {{reviews, salaries, health accommodations}} | High |
| Company financials & trade secrets | {{pricing models, pipelines, source code}} | High |
| Public/marketing content | {{website copy, published material}} | Low |

## 2. Data flow map

For each inventory entry that touches non-public data (from
`ai-inventory-template.md`):

| Inventory ID | Data going in | How it gets there | Vendor retention/training posture | Obligation implicated | Flow status |
|---|---|---|---|---|---|
| AI-01 | {{Internal docs, client names}} | {{Prompt paste}} | {{Team plan: no training on data; 30-day retention}} | {{Client confidentiality clauses}} | {{Acceptable with policy guardrail}} |
| AI-02 | {{Unknown; survey suggests client data}} | {{Personal accounts}} | {{Consumer default: may train on inputs}} | {{Confidentiality clauses; privacy policy}} | **Flag — counsel review** |
| AI-03 | {{Client call audio}} | {{Auto-join meeting AI}} | {{...}} | {{Recording-consent obligations vary by state — counsel}} | **Flag** |

## 3. Obligations inventory

What has the client promised, and where? (Reviewed documents, not legal
research.)

- **Client contracts:** {{confidentiality/data-handling clauses observed;
  e.g., "MSA §7 prohibits disclosure to third parties — whether AI vendors
  count is a counsel question."}}
- **Privacy policy:** {{what the public policy says about sharing/processing}}
- **Regulatory context (identification only):** {{e.g., CCPA/CPRA if
  California consumer data; HIPAA if health data; GDPR if EU subjects;
  sector rules. Named for counsel's attention, not analyzed.}}

## 4. Findings

| # | Finding | Evidence | Severity (1–5) | Disposition |
|---|---|---|---|---|
| P-1 | {{e.g., Client data in consumer AI accounts that may train on inputs}} | {{Survey Q10; AI-02}} | {{4}} | Remediate (→ remediation plan) + counsel review |
| P-2 | {{e.g., Meeting AI records client calls without consent language}} | {{AI-03}} | {{3}} | Counsel review |
| P-3 | {{e.g., No data-handling terms reviewed before tool adoption}} | {{Interviews}} | {{3}} | Remediate — intake gate covers this |

## 5. Recommended guardrails

1. **Account migration:** move work usage from personal to company accounts
   with training-off/enterprise data terms ({{tools}}).
2. **Data rules by category:** simple traffic-light table for employees —
   what can go into approved tools (green), what needs redaction (yellow),
   what never goes in (red: {{credentials, client PII, HR data}}).
3. **Vendor gate:** no new AI tool touches High-sensitivity data before a
   vendor assessment (see `vendor-tool-assessment.md`).
4. **Counsel review queue:** {{P-1, P-2}} routed to qualified counsel with
   this document as the factual record.

*Consulting work product — not legal advice. Sections 3–4 identify potential
legal issues for review by qualified counsel.*
