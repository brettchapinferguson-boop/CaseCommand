"""
CaseCommand — Intake Engine

Automated client intake with AI-powered case evaluation.
Analyzes intake information, identifies causes of action, maps facts to
prima facie elements, flags statute of limitations issues, and generates
a viability scorecard.

When a case is green-lighted, the intake data seeds a new case file with
enough structured information to immediately generate a complaint.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import httpx

from src.config import get_settings


# ---------------------------------------------------------------------------
# FEHA Prima Facie Element Templates
# ---------------------------------------------------------------------------

PRIMA_FACIE_TEMPLATES: dict[str, list[dict]] = {
    "FEHA_discrimination": [
        {"name": "Protected Class", "description": "Plaintiff is a member of a protected class", "statute": "Gov. Code §12940(a)"},
        {"name": "Qualification", "description": "Plaintiff was qualified for the position or performing competently", "statute": "Gov. Code §12940(a)"},
        {"name": "Adverse Action", "description": "Plaintiff suffered an adverse employment action", "statute": "Gov. Code §12940(a)"},
        {"name": "Circumstances Suggesting Discrimination", "description": "Circumstances suggest discriminatory motive (comparators, timing, statements)", "statute": "Gov. Code §12940(a)"},
    ],
    "FEHA_harassment": [
        {"name": "Protected Class", "description": "Plaintiff belongs to a protected class", "statute": "Gov. Code §12940(j)"},
        {"name": "Unwelcome Conduct", "description": "Plaintiff was subjected to unwelcome harassing conduct", "statute": "Gov. Code §12940(j)"},
        {"name": "Based on Protected Class", "description": "The harassment was based on plaintiff's protected characteristic", "statute": "Gov. Code §12940(j)"},
        {"name": "Severe or Pervasive", "description": "Conduct was sufficiently severe or pervasive to alter working conditions", "statute": "Gov. Code §12940(j)"},
        {"name": "Employer Liability", "description": "Employer knew or should have known and failed to take corrective action (or harasser was supervisor)", "statute": "Gov. Code §12940(j)"},
    ],
    "FEHA_retaliation": [
        {"name": "Protected Activity", "description": "Plaintiff engaged in protected activity (complained about discrimination, filed DFEH, etc.)", "statute": "Gov. Code §12940(h)"},
        {"name": "Adverse Action", "description": "Employer subjected plaintiff to adverse employment action", "statute": "Gov. Code §12940(h)"},
        {"name": "Causal Connection", "description": "There is a causal connection between the protected activity and adverse action (temporal proximity, statements, pattern)", "statute": "Gov. Code §12940(h)"},
    ],
    "failure_to_accommodate": [
        {"name": "Disability", "description": "Plaintiff has a physical or mental disability as defined by FEHA", "statute": "Gov. Code §12940(m)"},
        {"name": "Employer Knowledge", "description": "Employer knew of the disability", "statute": "Gov. Code §12940(m)"},
        {"name": "Accommodation Possible", "description": "A reasonable accommodation was available", "statute": "Gov. Code §12940(m)"},
        {"name": "Failure to Accommodate", "description": "Employer failed to provide reasonable accommodation", "statute": "Gov. Code §12940(m)"},
        {"name": "Harm", "description": "Plaintiff was harmed by the failure to accommodate", "statute": "Gov. Code §12940(m)"},
    ],
    "failure_to_engage_interactive_process": [
        {"name": "Disability", "description": "Plaintiff has a qualifying disability", "statute": "Gov. Code §12940(n)"},
        {"name": "Employer Knowledge", "description": "Employer knew of the need for accommodation", "statute": "Gov. Code §12940(n)"},
        {"name": "Failure to Engage", "description": "Employer failed to engage in a timely, good faith interactive process", "statute": "Gov. Code §12940(n)"},
        {"name": "Harm", "description": "Plaintiff was harmed by the failure to engage", "statute": "Gov. Code §12940(n)"},
    ],
    "wrongful_termination": [
        {"name": "Employment Relationship", "description": "An employer-employee relationship existed", "statute": "Common Law / Tameny"},
        {"name": "Termination", "description": "Employer terminated plaintiff's employment", "statute": "Common Law / Tameny"},
        {"name": "Violation of Public Policy", "description": "Termination violated a fundamental public policy (tethered to constitutional or statutory provision)", "statute": "Tameny v. Atlantic Richfield"},
        {"name": "Causation", "description": "The public policy violation was a substantial motivating factor in the termination", "statute": "Harris v. City of Santa Monica"},
    ],
    "CFRA_violation": [
        {"name": "Eligible Employee", "description": "Plaintiff worked for employer with 5+ employees for 12+ months, 1,250+ hours", "statute": "Gov. Code §12945.2"},
        {"name": "Qualifying Reason", "description": "Leave was for a qualifying reason (own serious health condition, family member, bonding)", "statute": "Gov. Code §12945.2"},
        {"name": "Denial or Retaliation", "description": "Employer denied leave, interfered, or retaliated against plaintiff for taking/requesting leave", "statute": "Gov. Code §12945.2"},
        {"name": "Harm", "description": "Plaintiff suffered harm as a result", "statute": "Gov. Code §12945.2"},
    ],
    "wage_theft": [
        {"name": "Employment Relationship", "description": "Plaintiff was an employee (not independent contractor)", "statute": "Lab. Code §1194"},
        {"name": "Wages Owed", "description": "Employer failed to pay wages due (overtime, minimum wage, meal/rest breaks, etc.)", "statute": "Lab. Code §§510, 1194, 226.7"},
        {"name": "Amount", "description": "Specific wages owed can be calculated", "statute": "Lab. Code §1194"},
    ],
    "failure_to_prevent": [
        {"name": "Employment Relationship", "description": "An employer-employee relationship existed", "statute": "Gov. Code §12940(k)"},
        {"name": "Underlying Violation", "description": "Plaintiff was subjected to discrimination, harassment, or retaliation", "statute": "Gov. Code §12940(k)"},
        {"name": "Failure to Prevent", "description": "Employer failed to take all reasonable steps to prevent the violation", "statute": "Gov. Code §12940(k)"},
        {"name": "Harm", "description": "The failure was a substantial factor in causing harm", "statute": "Gov. Code §12940(k)"},
    ],
    "IIED": [
        {"name": "Outrageous Conduct", "description": "Defendant engaged in extreme and outrageous conduct", "statute": "Common Law"},
        {"name": "Intent or Recklessness", "description": "Defendant intended to cause or recklessly disregarded the probability of causing emotional distress", "statute": "Common Law"},
        {"name": "Severe Distress", "description": "Plaintiff suffered severe or extreme emotional distress", "statute": "Common Law"},
        {"name": "Causation", "description": "Defendant's conduct was a substantial factor in causing the distress", "statute": "Common Law"},
    ],
}

# Statute of limitations (years from date of adverse action / last act)
SOL_MAP: dict[str, int] = {
    # FEHA claims: 3yr to file CRD complaint + 1yr from right-to-sue = 4yr total window
    # Using 3yr as base (CRD filing deadline per AB 9/SHARE Act, Gov. Code §12960)
    "FEHA_discrimination": 3,
    "FEHA_harassment": 3,
    "FEHA_retaliation": 3,
    "failure_to_accommodate": 3,
    "failure_to_engage_interactive_process": 3,
    "failure_to_prevent": 3,        # Gov. Code §12940(k) — derivative of FEHA
    "wrongful_termination": 2,      # 2 years — CCP §335.1 (personal injury)
    "CFRA_violation": 3,            # Gov. Code §12945.2
    "wage_theft": 3,                # CCP §338; 4 for UCL (Bus. & Prof. Code §17208)
    "breach_of_contract_written": 4,  # CCP §337
    "breach_of_contract_oral": 2,     # CCP §339
    "IIED": 2,                      # CCP §335.1
    "negligent_supervision": 2,      # CCP §335.1
}


# ---------------------------------------------------------------------------
# Intake Analyzer
# ---------------------------------------------------------------------------

class IntakeAnalyzer:
    """Analyzes client intake data and produces a case viability scorecard."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.settings = get_settings()

    async def analyze_intake(self, intake_data: dict) -> dict:
        """
        Full intake analysis pipeline:
        1. Identify potential causes of action
        2. Map facts to prima facie elements
        3. Check statute of limitations
        4. Identify affirmative defenses
        5. Generate viability score
        6. Return structured scorecard
        """
        # Step 1: Use AI to identify causes of action and map facts
        ai_analysis = await self._ai_analyze(intake_data)

        # Step 2: Build cause-of-action scorecards
        scorecards = []
        for coa in ai_analysis.get("causes_of_action", []):
            coa_type = coa.get("type", "")
            template = PRIMA_FACIE_TEMPLATES.get(coa_type, [])

            # Map facts to elements
            elements = []
            for tmpl_elem in template:
                elem = {
                    **tmpl_elem,
                    "satisfied": False,
                    "supporting_facts": [],
                    "missing_facts": [],
                }
                # Match AI-identified facts to this element
                for fact_map in coa.get("element_facts", []):
                    if fact_map.get("element") == tmpl_elem["name"]:
                        elem["satisfied"] = fact_map.get("satisfied", False)
                        elem["supporting_facts"] = fact_map.get("supporting_facts", [])
                        elem["missing_facts"] = fact_map.get("missing_facts", [])
                        break
                elements.append(elem)

            # SOL check
            sol_years = SOL_MAP.get(coa_type, 2)
            incident_date = intake_data.get("incident_date") or intake_data.get("termination_date")
            sol_date = None
            sol_status = "unknown"
            if incident_date:
                if isinstance(incident_date, str):
                    incident_date = date.fromisoformat(incident_date)
                sol_date = incident_date + timedelta(days=sol_years * 365)
                today = date.today()
                if sol_date < today:
                    sol_status = "expired"
                elif sol_date < today + timedelta(days=90):
                    sol_status = "expiring_soon"
                else:
                    sol_status = "active"

            # Affirmative defenses
            aff_defenses = coa.get("affirmative_defenses", [])

            # Score this COA
            satisfied_count = sum(1 for e in elements if e["satisfied"])
            total_elements = len(elements) if elements else 1
            element_score = (satisfied_count / total_elements) * 10

            # Adjust for SOL
            if sol_status == "expired":
                element_score *= 0.1
            elif sol_status == "expiring_soon":
                element_score *= 0.8

            # Adjust for fatal affirmative defenses
            fatal_defenses = [d for d in aff_defenses if d.get("risk_level") == "fatal"]
            if fatal_defenses:
                element_score *= 0.3

            scorecards.append({
                "cause_of_action": coa_type,
                "display_name": coa.get("display_name", coa_type.replace("_", " ").title()),
                "statute": coa.get("statute", ""),
                "elements": elements,
                "satisfied_count": satisfied_count,
                "total_elements": total_elements,
                "sol_date": sol_date.isoformat() if sol_date else None,
                "sol_status": sol_status,
                "sol_years": sol_years,
                "affirmative_defenses": aff_defenses,
                "score": round(element_score, 1),
                "viable": element_score >= 4.0 and sol_status != "expired",
            })

        # Overall case score
        if scorecards:
            viable_scores = [s["score"] for s in scorecards if s["viable"]]
            overall_score = max(viable_scores) if viable_scores else 0
        else:
            overall_score = 0

        # Recommendation
        if overall_score >= 7.0:
            recommendation = "accept"
        elif overall_score >= 4.0:
            recommendation = "needs_review"
        elif overall_score >= 2.0:
            recommendation = "needs_documents"
        else:
            recommendation = "decline"

        return {
            "scorecards": scorecards,
            "overall_score": round(overall_score, 1),
            "recommendation": recommendation,
            "ai_summary": ai_analysis.get("summary", ""),
            "ai_risk_assessment": ai_analysis.get("risk_assessment", {}),
            "recommended_discovery": ai_analysis.get("recommended_discovery", []),
            "estimated_value_range": ai_analysis.get("estimated_value_range", {}),
        }

    async def _ai_analyze(self, intake_data: dict) -> dict:
        """Use Claude to analyze intake data and identify causes of action."""
        system_prompt = """You are a California employment litigation expert analyzing a client intake.

Analyze the intake data and return a JSON object with:
1. "causes_of_action": array of potential claims, each with:
   - "type": one of the known types (FEHA_discrimination, FEHA_harassment, FEHA_retaliation, failure_to_accommodate, failure_to_engage_interactive_process, wrongful_termination, CFRA_violation, wage_theft)
   - "display_name": human-readable name
   - "statute": governing statute
   - "element_facts": array mapping facts to prima facie elements, each with:
     - "element": element name matching the template
     - "satisfied": boolean
     - "supporting_facts": array of fact strings from intake
     - "missing_facts": array of what's still needed
   - "affirmative_defenses": array of potential defenses, each with:
     - "defense": name
     - "risk_level": "low", "medium", "high", or "fatal"
     - "notes": explanation
2. "summary": 2-3 paragraph case summary
3. "risk_assessment": {strengths: [...], weaknesses: [...], red_flags: [...]}
4. "recommended_discovery": array of recommended discovery to pursue
5. "estimated_value_range": {low: number, mid: number, high: number, basis: string}

Return ONLY valid JSON. No markdown fences."""

        user_message = f"Analyze this client intake:\n\n{json.dumps(intake_data, indent=2, default=str)}"

        headers = {
            "x-api-key": self.settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=120.0, trust_env=False, proxy=self.settings.get_proxy()
        ) as client:
            resp = await client.post(
                f"{self.settings.ANTHROPIC_BASE_URL}/messages",
                headers=headers,
                json={
                    "model": self.settings.CLAUDE_MODEL,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text = data["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"causes_of_action": [], "summary": text, "risk_assessment": {}}

    async def save_intake(self, intake_data: dict, analysis: dict, org_id: str, user_id: str | None = None) -> dict:
        """Save intake record and cause-of-action scorecards to database."""
        if not self.db:
            return {"error": "Database not available"}

        # Build intake record
        record = {
            "org_id": org_id,
            "created_by": user_id,
            "client_first_name": intake_data.get("client_first_name", ""),
            "client_last_name": intake_data.get("client_last_name", ""),
            "client_email": intake_data.get("client_email"),
            "client_phone": intake_data.get("client_phone"),
            "client_address": intake_data.get("client_address"),
            "employer_name": intake_data.get("employer_name"),
            "employer_address": intake_data.get("employer_address"),
            "job_title": intake_data.get("job_title"),
            "hire_date": intake_data.get("hire_date"),
            "termination_date": intake_data.get("termination_date"),
            "employment_status": intake_data.get("employment_status"),
            "annual_salary": intake_data.get("annual_salary"),
            "supervisor_name": intake_data.get("supervisor_name"),
            "incident_date": intake_data.get("incident_date"),
            "incident_description": intake_data.get("incident_description"),
            "protected_class": intake_data.get("protected_class", []),
            "adverse_actions": intake_data.get("adverse_actions", []),
            "witnesses": json.dumps(intake_data.get("witnesses", [])),
            "prior_complaints": json.dumps(intake_data.get("prior_complaints", [])),
            "dfeh_filed": intake_data.get("dfeh_filed", False),
            "dfeh_filing_date": intake_data.get("dfeh_filing_date"),
            "dfeh_case_number": intake_data.get("dfeh_case_number"),
            "right_to_sue": intake_data.get("right_to_sue", False),
            "right_to_sue_date": intake_data.get("right_to_sue_date"),
            "ai_summary": analysis.get("ai_summary", ""),
            "ai_risk_assessment": json.dumps(analysis.get("ai_risk_assessment", {})),
            "overall_score": analysis.get("overall_score"),
            "recommended_action": analysis.get("recommendation"),
            "transcript": intake_data.get("transcript"),
            "source_channel": intake_data.get("source_channel", "web"),
            "status": "screening",
        }

        result = self.db.table("client_intakes").insert(record).execute()
        intake_id = result.data[0]["id"]

        # Save causes of action
        for sc in analysis.get("scorecards", []):
            coa_record = {
                "intake_id": intake_id,
                "org_id": org_id,
                "cause_of_action": sc["cause_of_action"],
                "statute_code": sc.get("statute", ""),
                "statute_of_limitations_date": sc.get("sol_date"),
                "sol_status": sc.get("sol_status"),
                "viable": sc.get("viable", False),
                "confidence_score": sc.get("score"),
                "prima_facie_elements": json.dumps(sc.get("elements", [])),
                "affirmative_defenses": json.dumps(sc.get("affirmative_defenses", [])),
            }
            self.db.table("intake_causes_of_action").insert(coa_record).execute()

        return {"intake_id": intake_id, "status": "screening"}

    async def greenlight_intake(self, intake_id: str, org_id: str, user_id: str) -> dict:
        """
        Accept an intake and create a case file from it.
        Seeds the case with all intake data, facts, and preliminary discovery.
        """
        if not self.db:
            return {"error": "Database not available"}

        # Fetch intake
        result = self.db.table("client_intakes").select("*").eq("id", intake_id).eq("org_id", org_id).execute()
        if not result.data:
            return {"error": "Intake not found"}
        intake = result.data[0]

        # Create case
        case_data = {
            "case_name": f"{intake['client_last_name']} v. {intake.get('employer_name', 'Unknown')}",
            "case_type": "Employment",
            "client_name": f"{intake['client_first_name']} {intake['client_last_name']}",
            "opposing_party": intake.get("employer_name", ""),
            "org_id": org_id,
            "user_id": user_id,
            "status": "active",
            "notes": intake.get("ai_summary", ""),
        }
        case_result = self.db.table("cases").insert(case_data).execute()
        case_id = case_result.data[0]["id"]

        # Update intake
        self.db.table("client_intakes").update({
            "status": "accepted",
            "case_id": case_id,
            "reviewed_by": user_id,
        }).eq("id", intake_id).execute()

        # Seed case facts from intake
        facts = []
        if intake.get("incident_description"):
            facts.append({
                "case_id": case_id,
                "org_id": org_id,
                "fact_text": intake["incident_description"],
                "fact_date": intake.get("incident_date"),
                "fact_type": "testimony",
                "source": "client intake interview",
                "importance": "high",
            })
        if intake.get("termination_date"):
            facts.append({
                "case_id": case_id,
                "org_id": org_id,
                "fact_text": f"Client terminated from employment at {intake.get('employer_name', 'employer')} on {intake['termination_date']}",
                "fact_date": intake["termination_date"],
                "fact_type": "document",
                "source": "client intake interview",
                "importance": "critical",
            })

        for fact in facts:
            self.db.table("case_facts").insert(fact).execute()

        return {
            "case_id": case_id,
            "case_name": case_data["case_name"],
            "intake_id": intake_id,
            "facts_seeded": len(facts),
        }
