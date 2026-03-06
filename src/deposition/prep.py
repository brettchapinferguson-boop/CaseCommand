"""
CaseCommand — Deposition Prep Engine

Comprehensive deposition preparation:
- Depo outline generation (taking and defending)
- Practice session simulation (avatar-style Q&A)
- Post-depo transcript analysis
- Impeachment material identification
"""

from __future__ import annotations

import json

import httpx

from src.config import get_settings


class DepositionPrep:
    """Generates deposition preparation materials and runs practice sessions."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.settings = get_settings()

    async def generate_outline(
        self,
        case_id: str,
        org_id: str,
        deponent_name: str,
        deponent_role: str,
        depo_type: str = "taking",
        areas_of_inquiry: list[str] | None = None,
    ) -> dict:
        """
        Generate a deposition outline.

        Args:
            depo_type: "taking" (you're deposing them) or "defending" (your client is being deposed)
        """
        context = await self._gather_context(case_id, org_id)

        if depo_type == "taking":
            system_prompt = f"""You are an expert California trial attorney preparing to take the deposition of {deponent_name} ({deponent_role}).

Generate a comprehensive deposition outline with:
1. Opening instructions (admonitions)
2. Background/foundation questions
3. Employment history specifics
4. Chronological incident questions
5. Document-specific examination areas
6. Damages-related questions
7. Witness identification questions
8. Closing lock-down questions

For each area, include:
- Strategic objective
- Specific questions (numbered)
- Documents to use (exhibit references)
- Pitfalls to avoid
- Key admissions to seek

{'Focus areas: ' + ', '.join(areas_of_inquiry) if areas_of_inquiry else ''}

Return JSON:
{{
    "areas_of_inquiry": [
        {{
            "area": "topic name",
            "objectives": ["what you want to establish"],
            "questions": ["specific questions"],
            "documents_to_use": ["document references"],
            "pitfalls": ["things to avoid"],
            "key_admissions": ["admissions to target"]
        }}
    ],
    "estimated_duration": "hours",
    "document_list": ["exhibits to prepare"],
    "strategic_notes": ["overall strategy notes"]
}}
Return ONLY valid JSON."""
        else:
            system_prompt = f"""You are an expert California trial attorney preparing {deponent_name} for their deposition as {deponent_role}.

Generate comprehensive deposition preparation materials:
1. General deposition rules and instructions
2. Anticipated questions by topic area
3. Suggested responses and approach for each area
4. Red flag areas to be careful about
5. Objection strategies for defending counsel

Return JSON:
{{
    "prep_instructions": "general instructions for the deponent",
    "anticipated_areas": [
        {{
            "area": "topic name",
            "likely_questions": ["questions opposing counsel will ask"],
            "guidance": "how to approach this area",
            "red_flags": ["things to watch out for"],
            "sample_responses": ["model response approaches"]
        }}
    ],
    "objection_strategy": "when and how to object during the depo",
    "dos_and_donts": {{
        "dos": ["things to do"],
        "donts": ["things to avoid"]
    }}
}}
Return ONLY valid JSON."""

        user_message = f"Case context:\n{json.dumps(context, indent=2, default=str)}"
        text = await self._call_ai(system_prompt, user_message)

        try:
            outline = json.loads(text)
        except json.JSONDecodeError:
            outline = {"raw_outline": text}

        # Save to database
        prep_id = None
        if self.db:
            record = {
                "case_id": case_id,
                "org_id": org_id,
                "deponent_name": deponent_name,
                "deponent_role": deponent_role,
                "deposition_type": "oral",
                "outline": text,
                "areas_of_inquiry": json.dumps(outline.get("areas_of_inquiry", outline.get("anticipated_areas", []))),
                "status": "preparing",
            }
            if depo_type == "defending":
                record["prep_instructions"] = outline.get("prep_instructions", "")
                record["anticipated_questions"] = json.dumps(outline.get("anticipated_areas", []))

            result = self.db.table("deposition_preps").insert(record).execute()
            prep_id = result.data[0]["id"] if result.data else None

        outline["prep_id"] = prep_id
        outline["depo_type"] = depo_type
        return outline

    async def practice_session(
        self,
        prep_id: str,
        deponent_answer: str,
        question_area: str | None = None,
    ) -> dict:
        """
        Simulate a deposition practice session.
        The AI acts as opposing counsel asking questions.
        The deponent (client) responds, and AI provides feedback.
        """
        # Get prep context
        if self.db:
            prep = self.db.table("deposition_preps").select("*").eq("id", prep_id).execute()
            if not prep.data:
                return {"error": "Prep record not found"}
            prep_data = prep.data[0]
        else:
            prep_data = {}

        system_prompt = """You are an experienced opposing counsel conducting a practice deposition.

Based on the deponent's response, provide:
1. A follow-up question (as opposing counsel would)
2. Feedback on the deponent's answer:
   - Was it too long? (depositions favor short answers)
   - Did they volunteer information?
   - Did they speculate?
   - Was there a better way to answer?
3. A score from 1-10
4. Coaching tip

Return JSON:
{
    "follow_up_question": "next question opposing counsel would ask",
    "feedback": {
        "score": number (1-10),
        "strengths": ["what was good"],
        "weaknesses": ["what could be improved"],
        "coaching_tip": "specific advice",
        "better_response": "how they should have answered (if applicable)"
    }
}
Return ONLY valid JSON."""

        user_message = f"""Deposition prep context:
Deponent: {prep_data.get('deponent_name', 'Unknown')}
Role: {prep_data.get('deponent_role', 'Unknown')}
{'Current area: ' + question_area if question_area else ''}

Deponent's answer: "{deponent_answer}"
"""

        text = await self._call_ai(system_prompt, user_message)

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {"feedback": {"raw": text}}

        return result

    async def analyze_transcript(
        self,
        case_id: str,
        org_id: str,
        prep_id: str,
        transcript_text: str,
    ) -> dict:
        """
        Analyze a completed deposition transcript.
        Identifies key admissions, impeachment material, and strategic insights.
        """
        system_prompt = """You are an expert litigation attorney analyzing a deposition transcript.

Provide comprehensive analysis:
1. Key admissions made by the deponent
2. Inconsistencies with prior statements or documents
3. Impeachment material (contradictions, lack of knowledge, bias)
4. Key testimony supporting our case theory
5. Key testimony undermining our case
6. Witnesses or documents identified for follow-up
7. Areas requiring supplemental discovery

Return JSON:
{
    "summary": "executive summary of the deposition",
    "key_admissions": [
        {"page_line": "p.X:Y", "admission": "what was admitted", "significance": "why it matters"}
    ],
    "impeachment_material": [
        {"page_line": "p.X:Y", "testimony": "what was said", "contradicts": "what it contradicts", "usability": "how to use at trial"}
    ],
    "favorable_testimony": [
        {"page_line": "p.X:Y", "testimony": "summary", "supports": "which element/theory"}
    ],
    "unfavorable_testimony": [
        {"page_line": "p.X:Y", "testimony": "summary", "impact": "assessment"}
    ],
    "follow_up_needed": [
        {"item": "what needs follow-up", "type": "discovery | deposition | investigation"}
    ],
    "trial_designations": ["key excerpts to designate for trial"]
}
Return ONLY valid JSON."""

        user_message = f"Analyze this deposition transcript:\n\n{transcript_text}"
        text = await self._call_ai(system_prompt, user_message)

        try:
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {"summary": text}

        # Update prep record
        if self.db:
            self.db.table("deposition_preps").update({
                "ai_summary": analysis.get("summary", ""),
                "key_admissions": json.dumps(analysis.get("key_admissions", [])),
                "impeachment_material": json.dumps(analysis.get("impeachment_material", [])),
                "status": "summarized",
            }).eq("id", prep_id).execute()

            # Inject key admissions as case facts
            for admission in analysis.get("key_admissions", []):
                self.db.table("case_facts").insert({
                    "case_id": case_id,
                    "org_id": org_id,
                    "fact_text": admission.get("admission", ""),
                    "fact_type": "admission",
                    "source": f"Deposition of {prep_id}",
                    "importance": "high",
                }).execute()

        return analysis

    async def _gather_context(self, case_id: str, org_id: str) -> dict:
        """Gather case context for depo prep."""
        context: dict = {"case_id": case_id}
        if not self.db:
            return context

        case = self.db.table("cases").select("*").eq("id", case_id).execute()
        if case.data:
            context.update(case.data[0])

        facts = self.db.table("case_facts").select("*").eq("case_id", case_id).execute()
        context["facts"] = facts.data or []

        intake = self.db.table("client_intakes").select("*").eq("case_id", case_id).limit(1).execute()
        if intake.data:
            context["intake"] = intake.data[0]
            coa = self.db.table("intake_causes_of_action").select("*").eq("intake_id", intake.data[0]["id"]).execute()
            context["causes_of_action"] = coa.data or []

        discovery = self.db.table("discovery_sets").select("*").eq("case_id", case_id).execute()
        context["discovery"] = discovery.data or []

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
