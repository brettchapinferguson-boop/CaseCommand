# Vendor & Tool Assessment

**Client:** {{Client Company}} · **Date:** {{Date}}

> GUIDANCE: One assessment sheet per vendor (VTA-01, VTA-02, ...), linked
> from the inventory. The value is plain English: translate the vendor's
> terms into what they actually mean for this client's data. Quote and pin
> the exact terms version reviewed — AI vendor terms change often.

---

## Assessment sheet — VTA-{{NN}}

**Tool:** {{name + plan/tier — tier matters: consumer vs. enterprise terms
differ radically}}
**Vendor:** {{company}} · **Inventory refs:** {{AI-xx}}
**Terms reviewed:** {{URLs + version/date}} · **Reviewed by:** {{Consultant}}

### 1. Data handling — plain English

| Question | Vendor's answer (cite section) | What it means here |
|---|---|---|
| Is customer input used to train models? | {{e.g., "Not for Team/Enterprise tiers (Terms §X); yes by default on consumer tier"}} | {{e.g., "Safe on the company plan; the 14 personal accounts are a different story"}} |
| How long are prompts/outputs retained? | {{...}} | |
| Can retention be reduced/zeroed? | {{...}} | |
| Where is data processed/stored? | {{...}} | |
| Is a DPA offered? Signed? | {{Offered: Y/N · Signed: Y/N}} | |
| Do subprocessors get the data? | {{...}} | |
| Human review of inputs by vendor staff? | {{...}} | |

### 2. Security posture

- Certifications claimed: {{SOC 2 Type II / ISO 27001 / none found}}
- SSO/SAML support: {{Y/N}} · Admin controls & audit logs: {{Y/N/partial}}
- Breach notification commitment: {{terms, timeframe}}
- Known incidents: {{public record search result}}

### 3. Commercial and continuity

- Plan in use vs. plan the data terms assume: {{mismatch is the #1 finding
  in practice}}
- Ownership of outputs per terms: {{...}}
- Indemnity offered (e.g., copyright): {{...}}
- Lock-in/export: {{can data/configs be exported?}}
- Vendor viability note: {{funding/scale — flag single-founder tools holding
  critical data}}

### 4. Verdict

**Rating:** {{Approved / Approved with conditions / Migrate tier / Replace / Prohibit}}

**Conditions:** {{e.g., "Approved only on Team tier with training-off
confirmed; sign DPA; disable X feature; add to quarterly re-check."}}

**Risk feed:** contributes to Vendor dimension score of {{N}} in the
scorecard because {{one sentence}}.

---

## Assessment summary (all vendors)

| ID | Tool | Tier | Trains on data? | DPA | Verdict |
|---|---|---|---|---|---|
| VTA-01 | {{...}} | {{...}} | {{No (enterprise)}} | {{Signed}} | Approved w/ conditions |
| VTA-02 | {{...}} | | | | |

**Re-review cadence:** quarterly, or on any vendor terms-change
notification (inventory owner watches for these — see tracking system).
