"""
CaseCommand — Law & Motion Engine

Drafts motions and pleadings, with an oversight agent that identifies
when and where certain motions should be filed.

Capabilities:
- Generate complaints from intake data
- Draft any motion or pleading type
- Oversight agent: proactively flags motion opportunities and deadlines
- Opposition and reply drafting
- Separate statement generation (CRC 3.1345)
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import httpx

from src.config import get_settings


# ---------------------------------------------------------------------------
# California Motion Timing Rules
# ---------------------------------------------------------------------------

MOTION_TIMING = {
    "demurrer": {
        "deadline_from_service": 30,
        "hearing_notice_days": 16,
        "opposition_days_before": 9,
        "reply_days_before": 5,
        "ccp_section": "CCP §430.40",
    },
    "motion_to_compel": {
        "deadline_from_service": 45,
        "hearing_notice_days": 16,
        "opposition_days_before": 9,
        "reply_days_before": 5,
        "ccp_section": "CCP §2030.300",
        "requires_meet_confer": True,
        "requires_separate_statement": True,
    },
    "msj": {
        "filing_deadline_before_trial": 81,   # AB 2049 (2025): 81 days notice
        "hearing_notice_days": 81,
        "opposition_days_before": 20,          # AB 2049: 20 days (was 14)
        "reply_days_before": 11,               # AB 2049: 11 days (was 5)
        "ccp_section": "CCP §437c (as amended AB 2049)",
        "requires_separate_statement": True,
    },
    "motion_in_limine": {
        "typical_deadline": "per local rule or court order",
        "ccp_section": "CCP §402",
    },
    "motion_to_strike": {
        "deadline_from_service": 30,
        "hearing_notice_days": 16,
        "opposition_days_before": 9,
        "reply_days_before": 5,
        "ccp_section": "CCP §435",
    },
    "ex_parte": {
        "notice_hours": 24,
        "ccp_section": "CRC 3.1200-3.1207",
    },
    "motion_for_sanctions": {
        "safe_harbor_days": 21,
        "hearing_notice_days": 16,
        "ccp_section": "CCP §128.7",
    },
}


class MotionEngine:
    """Generates legal motions, pleadings, and provides oversight analysis."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # Complaint Generation
    # ------------------------------------------------------------------

    async def generate_complaint(self, case_id: str, org_id: str) -> dict:
        """
        Generate a complaint from intake data and case facts.
        This is the foundational document from which all litigation flows.
        """
        context = await self._gather_full_context(case_id, org_id)

        system_prompt = """You are an expert California employment litigation attorney.
Draft a complete Complaint for the given case. Follow California Superior Court formatting:

1. Caption with proper court heading
2. Parties section
3. General Allegations (factual background)
4. Each Cause of Action as a separate count with:
   - Incorporation by reference
   - All prima facie elements alleged
   - Specific statutory references
   - Damages paragraph
5. Prayer for Relief (general damages, special damages, punitive damages, attorney fees, injunctive relief)
6. Jury demand

Use the firm identity from context for attorney information.
Apply proper paragraph numbering.
Reference FEHA (Gov. Code §12940 et seq.) and all applicable statutes.
Include CACI jury instruction references where relevant.

Return the full complaint text in markdown format."""

        user_message = f"Generate complaint for:\n{json.dumps(context, indent=2, default=str)}"
        text = await self._call_ai(system_prompt, user_message)

        # Save motion record
        motion_id = None
        if self.db:
            record = {
                "case_id": case_id,
                "org_id": org_id,
                "motion_type": "complaint",
                "title": f"Complaint — {context.get('case_name', 'Case')}",
                "filing_party": "plaintiff",
                "status": "draft",
                "ai_generated": True,
                "ai_draft": text,
            }
            result = self.db.table("motions").insert(record).execute()
            motion_id = result.data[0]["id"] if result.data else None

        return {
            "motion_id": motion_id,
            "type": "complaint",
            "title": f"Complaint — {context.get('case_name', '')}",
            "body": text,
        }

    # ------------------------------------------------------------------
    # General Motion Drafting
    # ------------------------------------------------------------------

    async def draft_motion(
        self,
        case_id: str,
        org_id: str,
        motion_type: str,
        filing_party: str = "plaintiff",
        additional_context: str = "",
        target_issues: list[str] | None = None,
    ) -> dict:
        """Draft any motion type with full California formatting."""
        context = await self._gather_full_context(case_id, org_id)
        timing = MOTION_TIMING.get(motion_type, {})

        type_guidance = {
            "demurrer": "Draft a Demurrer per CCP §430.10. Include each ground for demurrer and supporting case law.",
            "motion_to_compel": "Draft a Motion to Compel Further Responses per CCP §2030.300/2031.310. Include meet and confer declaration (CCP §2016.040) and separate statement (CRC 3.1345).",
            "msj": "Draft a Motion for Summary Judgment per CCP §437c. Include separate statement of undisputed material facts with evidence citations.",
            "msa": "Draft a Motion for Summary Adjudication per CCP §437c(f). Target specific causes of action or issues.",
            "motion_in_limine": "Draft Motions in Limine. Each motion should be a separate, numbered motion with clear ruling requested.",
            "motion_to_strike": "Draft a Motion to Strike per CCP §435-436. Identify irrelevant, false, or improper matter.",
            "ex_parte": "Draft an Ex Parte Application per CRC 3.1200-3.1207. Include declaration showing irreparable harm and notice given.",
            "motion_for_sanctions": "Draft a Motion for Sanctions per CCP §128.7. Include safe harbor notice documentation.",
            "opposition": "Draft an Opposition to the opposing party's motion. Address each argument and cite contrary authority.",
            "reply": "Draft a Reply brief. Address opposition arguments point by point. Keep concise per local rules.",
            "motion_for_protective_order": "Draft a Motion for Protective Order per CCP §2030.090. Include good cause showing.",
        }

        system_prompt = f"""You are an expert California litigation attorney drafting a {motion_type.replace('_', ' ')}.

{type_guidance.get(motion_type, f'Draft a {motion_type.replace("_", " ")} with proper California formatting.')}

{'Requires separate statement per CRC 3.1345.' if timing.get('requires_separate_statement') else ''}
{'Requires meet and confer declaration per CCP §2016.040.' if timing.get('requires_meet_confer') else ''}

Format the motion with:
1. Caption
2. Notice of Motion
3. Memorandum of Points and Authorities
4. Declaration(s) in support
5. Proposed Order
{'6. Separate Statement' if timing.get('requires_separate_statement') else ''}

Use the firm identity for attorney information. Apply proper California court formatting.
{'Target issues: ' + ', '.join(target_issues) if target_issues else ''}

Return the full motion in markdown format."""

        user_message = f"""Case context:
{json.dumps(context, indent=2, default=str)}

Motion type: {motion_type}
Filing party: {filing_party}
{f'Additional context: {additional_context}' if additional_context else ''}"""

        text = await self._call_ai(system_prompt, user_message)

        # Calculate dates
        hearing_date = None
        opposition_due = None
        reply_due = None
        if timing:
            notice_days = timing.get("hearing_notice_days", 16)
            hearing_date = date.today() + timedelta(days=notice_days + 10)
            opp_days = timing.get("opposition_days_before", 9)
            reply_days = timing.get("reply_days_before", 5)
            opposition_due = hearing_date - timedelta(days=opp_days)
            reply_due = hearing_date - timedelta(days=reply_days)

        # Save
        motion_id = None
        if self.db:
            record = {
                "case_id": case_id,
                "org_id": org_id,
                "motion_type": motion_type,
                "title": f"{motion_type.replace('_', ' ').title()} — {context.get('case_name', '')}",
                "filing_party": filing_party,
                "hearing_date": hearing_date.isoformat() if hearing_date else None,
                "opposition_due": opposition_due.isoformat() if opposition_due else None,
                "reply_due": reply_due.isoformat() if reply_due else None,
                "status": "draft",
                "ai_generated": True,
                "ai_draft": text,
            }
            result = self.db.table("motions").insert(record).execute()
            motion_id = result.data[0]["id"] if result.data else None

            # Auto-create calendar deadlines
            if hearing_date:
                deadlines = [
                    {"title": f"Hearing: {motion_type.replace('_', ' ').title()}", "deadline_date": hearing_date.isoformat(), "deadline_type": "hearing", "priority": "high"},
                ]
                if opposition_due:
                    deadlines.append({"title": f"Opposition due: {motion_type.replace('_', ' ').title()}", "deadline_date": opposition_due.isoformat(), "deadline_type": "filing", "priority": "high"})
                if reply_due:
                    deadlines.append({"title": f"Reply due: {motion_type.replace('_', ' ').title()}", "deadline_date": reply_due.isoformat(), "deadline_type": "filing", "priority": "normal"})

                for dl in deadlines:
                    dl.update({"case_id": case_id, "org_id": org_id, "auto_generated": True, "source": timing.get("ccp_section", "")})
                    self.db.table("case_deadlines").insert(dl).execute()

        return {
            "motion_id": motion_id,
            "type": motion_type,
            "title": f"{motion_type.replace('_', ' ').title()}",
            "body": text,
            "hearing_date": hearing_date.isoformat() if hearing_date else None,
            "opposition_due": opposition_due.isoformat() if opposition_due else None,
            "reply_due": reply_due.isoformat() if reply_due else None,
        }

    # ------------------------------------------------------------------
    # Oversight Agent
    # ------------------------------------------------------------------

    async def oversight_analysis(self, case_id: str, org_id: str) -> dict:
        """
        Oversight agent: reviews case status and identifies:
        1. Motions that should be considered at this stage
        2. Deadlines that are approaching
        3. Opportunities for strategic motions
        4. Potential vulnerabilities requiring defensive motions
        """
        context = await self._gather_full_context(case_id, org_id)

        system_prompt = """You are a senior litigation strategist reviewing a case file.
Analyze the current case status and identify motion opportunities and risks.

Return JSON:
{
    "recommended_motions": [
        {
            "motion_type": string,
            "reason": string,
            "urgency": "immediate" | "soon" | "consider" | "monitor",
            "deadline": string or null,
            "ccp_section": string
        }
    ],
    "defensive_alerts": [
        {
            "risk": string,
            "potential_opposing_motion": string,
            "recommended_response": string,
            "urgency": string
        }
    ],
    "deadline_warnings": [
        {
            "deadline": string,
            "description": string,
            "days_remaining": number,
            "action_needed": string
        }
    ],
    "strategic_observations": [string]
}
Return ONLY valid JSON."""

        user_message = f"Review this case for motion opportunities:\n{json.dumps(context, indent=2, default=str)}"
        text = await self._call_ai(system_prompt, user_message)

        try:
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {"recommended_motions": [], "strategic_observations": [text]}

        # Save oversight flags to existing motions
        if self.db and analysis.get("recommended_motions"):
            for rec in analysis["recommended_motions"]:
                if rec.get("urgency") in ("immediate", "soon"):
                    # Check if motion already exists
                    existing = (
                        self.db.table("motions")
                        .select("id")
                        .eq("case_id", case_id)
                        .eq("motion_type", rec["motion_type"])
                        .execute()
                    )
                    if not existing.data:
                        # Flag for attorney review
                        self.db.table("motions").insert({
                            "case_id": case_id,
                            "org_id": org_id,
                            "motion_type": rec["motion_type"],
                            "title": f"[OVERSIGHT] {rec['motion_type'].replace('_', ' ').title()} — Recommended",
                            "status": "flagged",
                            "ai_analysis": rec["reason"],
                            "oversight_flags": json.dumps([{
                                "flag": rec["reason"],
                                "severity": "high" if rec["urgency"] == "immediate" else "medium",
                                "recommendation": rec.get("ccp_section", ""),
                            }]),
                        }).execute()

        return analysis

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _gather_full_context(self, case_id: str, org_id: str) -> dict:
        """Gather complete case context for motion generation."""
        context: dict = {"case_id": case_id}

        if not self.db:
            return context

        # Case
        case = self.db.table("cases").select("*").eq("id", case_id).execute()
        if case.data:
            context.update(case.data[0])

        # Firm config
        try:
            firm = self.db.table("firm_config").select("*").eq("org_id", org_id).execute()
            if firm.data:
                context["firm"] = firm.data[0]
        except Exception:
            pass

        # Intake
        intake = self.db.table("client_intakes").select("*").eq("case_id", case_id).limit(1).execute()
        if intake.data:
            context["intake"] = intake.data[0]
            # COA
            coa = self.db.table("intake_causes_of_action").select("*").eq("intake_id", intake.data[0]["id"]).execute()
            context["causes_of_action"] = coa.data or []

        # Facts
        facts = self.db.table("case_facts").select("*").eq("case_id", case_id).execute()
        context["facts"] = facts.data or []

        # Existing motions
        motions = self.db.table("motions").select("*").eq("case_id", case_id).execute()
        context["existing_motions"] = motions.data or []

        # Discovery status
        discovery = self.db.table("discovery_sets").select("*").eq("case_id", case_id).execute()
        context["discovery"] = discovery.data or []

        # Deadlines
        deadlines = self.db.table("case_deadlines").select("*").eq("case_id", case_id).order("deadline_date").execute()
        context["deadlines"] = deadlines.data or []

        return context

    async def _call_ai(self, system_prompt: str, user_message: str) -> str:
        """Call Claude API."""
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
                    "max_tokens": 8192,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
