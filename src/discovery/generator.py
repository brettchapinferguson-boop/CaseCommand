"""
CaseCommand — Discovery Generator

Generates complete discovery sets from case data:
- Form Interrogatories (Employment)
- Special Interrogatories
- Requests for Production of Documents
- Requests for Admission
- Deposition Notices
- Subpoenas Duces Tecum

Discovery is auto-drafted at complaint filing and updated as new
information enters the case file. Builds on intake facts and
prima facie elements to target specific evidentiary gaps.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import httpx

from src.config import get_settings


# ---------------------------------------------------------------------------
# California Form Interrogatory Templates (Employment)
# ---------------------------------------------------------------------------

FORM_INTERROGATORIES_EMPLOYMENT = [
    {"number": "200.1", "text": "State the date you were hired by the DEFENDANT."},
    {"number": "200.2", "text": "State all job titles or positions held during your employment."},
    {"number": "200.3", "text": "State your rate(s) of pay at the time of the INCIDENT and at the time of termination."},
    {"number": "200.4", "text": "State the names of your supervisors during the relevant period."},
    {"number": "200.5", "text": "Describe the circumstances of the termination of your employment."},
    {"number": "200.6", "text": "Identify all persons who witnessed or have knowledge of the INCIDENT."},
    {"number": "200.7", "text": "Have you filed any complaints with government agencies regarding the INCIDENT?"},
    {"number": "200.8", "text": "Identify all documents that support your claims."},
    {"number": "200.9", "text": "State whether you have obtained new employment since the INCIDENT."},
    {"number": "200.10", "text": "State all damages you claim as a result of the INCIDENT."},
]


class DiscoveryGenerator:
    """Generates discovery sets tailored to specific case facts and claims."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.settings = get_settings()

    async def generate_discovery_set(
        self,
        case_id: str,
        org_id: str,
        set_type: str,
        direction: str = "propounding",
        target_elements: list[str] | None = None,
        additional_context: str = "",
    ) -> dict:
        """
        Generate a full discovery set for a case.

        Args:
            case_id: The case to generate discovery for.
            set_type: form_interrogatories, special_interrogatories, rfp, rfa,
                      deposition_notice, subpoena_duces_tecum
            direction: propounding or responding
            target_elements: Specific prima facie elements to target.
            additional_context: Any additional info to guide generation.
        """
        # Gather case context
        case_context = await self._gather_case_context(case_id, org_id)

        if set_type == "form_interrogatories":
            items = FORM_INTERROGATORIES_EMPLOYMENT
            ai_items = []
        else:
            # Use AI to generate tailored discovery
            ai_items = await self._ai_generate_discovery(
                case_context=case_context,
                set_type=set_type,
                direction=direction,
                target_elements=target_elements or [],
                additional_context=additional_context,
            )
            items = ai_items

        # Determine set number
        if self.db:
            existing = (
                self.db.table("discovery_sets")
                .select("set_number")
                .eq("case_id", case_id)
                .eq("set_type", set_type)
                .eq("direction", direction)
                .order("set_number", desc=True)
                .limit(1)
                .execute()
            )
            set_number = (existing.data[0]["set_number"] + 1) if existing.data else 1
        else:
            set_number = 1

        # Calculate dates
        served_date = date.today()
        if direction == "propounding":
            due_date = served_date + timedelta(days=30)  # CCP 2030.260
        else:
            due_date = served_date + timedelta(days=30)

        result = {
            "set_type": set_type,
            "set_number": set_number,
            "direction": direction,
            "served_date": served_date.isoformat(),
            "due_date": due_date.isoformat(),
            "items": items,
            "item_count": len(items),
            "case_context_used": {
                "case_name": case_context.get("case_name", ""),
                "causes_of_action": case_context.get("causes_of_action", []),
            },
        }

        # Save to database
        if self.db:
            set_record = {
                "case_id": case_id,
                "org_id": org_id,
                "set_type": set_type,
                "set_number": set_number,
                "direction": direction,
                "served_date": served_date.isoformat(),
                "due_date": due_date.isoformat(),
                "status": "draft",
                "ai_generated": True,
            }
            set_result = self.db.table("discovery_sets").insert(set_record).execute()
            set_id = set_result.data[0]["id"]
            result["set_id"] = set_id

            # Save individual items
            for i, item in enumerate(items):
                item_record = {
                    "set_id": set_id,
                    "item_number": i + 1,
                    "request_text": item.get("text", item.get("request_text", "")),
                    "targeted_elements": item.get("targeted_elements", []),
                }
                self.db.table("discovery_items").insert(item_record).execute()

        return result

    async def generate_offensive_package(self, case_id: str, org_id: str) -> dict:
        """
        Generate the complete offensive discovery package at complaint filing:
        - Form Interrogatories (Employment)
        - Special Interrogatories, Set One
        - Requests for Production, Set One
        - Requests for Admission, Set One
        """
        results = {}

        for set_type in ["form_interrogatories", "special_interrogatories", "rfp", "rfa"]:
            result = await self.generate_discovery_set(
                case_id=case_id,
                org_id=org_id,
                set_type=set_type,
                direction="propounding",
            )
            results[set_type] = result

        return {
            "case_id": case_id,
            "package": "offensive",
            "sets_generated": len(results),
            "sets": results,
        }

    async def analyze_responses(
        self, set_id: str, responses: list[dict]
    ) -> dict:
        """
        Analyze discovery responses received from opposing party.
        Flags boilerplate objections, evasive answers, admissions.
        """
        system_prompt = """You are a California litigation discovery expert.
Analyze each discovery response and return a JSON array where each item has:
- "item_number": int
- "analysis": string (concise analysis)
- "flags": array of strings from: ["evasive", "boilerplate_objection", "admission", "inconsistent", "privilege_claimed", "incomplete", "responsive"]
- "follow_up_needed": boolean
- "follow_up_text": string (suggested follow-up request or motion to compel argument if needed)
- "key_admission": string or null (if this response contains a useful admission)

Focus on: Korea Data Systems (boilerplate objections), Deyo v. Kilbourne (evasive responses),
CCP 2030.300 (motions to compel further), and CCP 2033.280 (deemed admissions).
Return ONLY valid JSON array."""

        user_message = "Analyze these discovery responses:\n\n"
        for r in responses:
            user_message += f"Request {r['item_number']}:\n{r.get('request_text', '')}\n\n"
            user_message += f"Response:\n{r.get('response_text', '')}\n\n---\n\n"

        analysis = await self._call_ai(system_prompt, user_message)

        try:
            items_analysis = json.loads(analysis)
        except json.JSONDecodeError:
            items_analysis = []

        # Update items in database
        if self.db and items_analysis:
            for item in items_analysis:
                self.db.table("discovery_items").update({
                    "ai_analysis": item.get("analysis", ""),
                    "analysis_flags": item.get("flags", []),
                    "follow_up_needed": item.get("follow_up_needed", False),
                    "follow_up_text": item.get("follow_up_text", ""),
                }).eq("set_id", set_id).eq("item_number", item.get("item_number")).execute()

        # Determine if meet and confer is needed
        flagged_items = [i for i in items_analysis if i.get("follow_up_needed")]
        if flagged_items:
            if self.db:
                self.db.table("discovery_sets").update({
                    "status": "analyzed",
                    "meet_confer_status": "pending",
                    "ai_analysis": f"{len(flagged_items)} items require follow-up",
                }).eq("id", set_id).execute()

        return {
            "set_id": set_id,
            "total_items": len(responses),
            "flagged_items": len(flagged_items),
            "admissions_found": sum(1 for i in items_analysis if "admission" in i.get("flags", [])),
            "analysis": items_analysis,
        }

    async def inject_new_information(
        self, case_id: str, org_id: str, new_facts: list[str]
    ) -> dict:
        """
        When new information enters the case, determine if additional
        discovery should be propounded and generate supplemental requests.
        """
        case_context = await self._gather_case_context(case_id, org_id)

        system_prompt = """You are a California litigation discovery expert.
Given new facts that have come to light in a case, determine:
1. Should supplemental discovery be propounded? (yes/no)
2. Which type of discovery is most appropriate?
3. Generate specific discovery requests targeting this new information.

Return JSON:
{
    "should_supplement": boolean,
    "reasoning": string,
    "suggested_sets": [
        {
            "set_type": "special_interrogatories" | "rfp" | "rfa",
            "items": [{"text": "...", "targeted_elements": [...]}]
        }
    ]
}
Return ONLY valid JSON."""

        user_message = f"""Case context:
{json.dumps(case_context, indent=2, default=str)}

New facts discovered:
{json.dumps(new_facts, indent=2)}"""

        analysis = await self._call_ai(system_prompt, user_message)

        try:
            result = json.loads(analysis)
        except json.JSONDecodeError:
            result = {"should_supplement": False, "reasoning": analysis}

        # Auto-generate supplemental sets if recommended
        if result.get("should_supplement") and self.db:
            for suggested in result.get("suggested_sets", []):
                await self.generate_discovery_set(
                    case_id=case_id,
                    org_id=org_id,
                    set_type=suggested["set_type"],
                    direction="propounding",
                    additional_context=f"Supplemental based on new facts: {json.dumps(new_facts)}",
                )

        return result

    async def _gather_case_context(self, case_id: str, org_id: str) -> dict:
        """Gather all relevant case information for discovery generation."""
        context: dict = {"case_id": case_id}

        if not self.db:
            return context

        # Case details
        case = self.db.table("cases").select("*").eq("id", case_id).execute()
        if case.data:
            context.update(case.data[0])

        # Intake data (if exists)
        intake = self.db.table("client_intakes").select("*").eq("case_id", case_id).limit(1).execute()
        if intake.data:
            context["intake"] = intake.data[0]

        # Causes of action
        if intake.data:
            coa = (
                self.db.table("intake_causes_of_action")
                .select("*")
                .eq("intake_id", intake.data[0]["id"])
                .execute()
            )
            context["causes_of_action"] = coa.data or []

        # Existing facts
        facts = self.db.table("case_facts").select("*").eq("case_id", case_id).execute()
        context["facts"] = facts.data or []

        # Existing discovery (to avoid duplication)
        existing = self.db.table("discovery_sets").select("set_type, set_number, status").eq("case_id", case_id).execute()
        context["existing_discovery"] = existing.data or []

        return context

    async def _ai_generate_discovery(
        self,
        case_context: dict,
        set_type: str,
        direction: str,
        target_elements: list[str],
        additional_context: str,
    ) -> list[dict]:
        """Use AI to generate tailored discovery requests."""
        type_guidance = {
            "special_interrogatories": "Generate 25-35 special interrogatories. Each should target specific facts, identify witnesses, or establish elements of the claims. Use CCP 2030.010 format.",
            "rfp": "Generate 25-40 requests for production of documents. Target employment records, communications, policies, personnel files, and documents supporting the claims. Use CCP 2031.010 format.",
            "rfa": "Generate 15-25 requests for admission. Target key facts that are likely undisputed or that will be costly for the opposing party to deny. Use CCP 2033.010 format.",
            "deposition_notice": "Generate a deposition notice with areas of inquiry. Include all topics to be covered per CCP 2025.230.",
            "subpoena_duces_tecum": "Generate document requests for a third-party subpoena. Include all relevant records categories.",
        }

        system_prompt = f"""You are a California employment litigation discovery expert.
Generate {set_type.replace('_', ' ')} for the {direction} party.

{type_guidance.get(set_type, '')}

{'Target these prima facie elements: ' + ', '.join(target_elements) if target_elements else ''}

Return a JSON array where each item has:
- "text": the full text of the request
- "targeted_elements": array of prima facie elements this request targets
- "purpose": brief note on strategic purpose

Apply California formatting rules. Reference CCP sections where applicable.
Return ONLY valid JSON array."""

        user_message = f"""Case context:
{json.dumps(case_context, indent=2, default=str)}

{f'Additional context: {additional_context}' if additional_context else ''}"""

        result = await self._call_ai(system_prompt, user_message)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    async def _call_ai(self, system_prompt: str, user_message: str) -> str:
        """Call Claude API and return the response text."""
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

        return data["content"][0]["text"]
