"""
CaseCommand — Contract Reviewer

AI-powered contract analysis for:
- Employment agreements
- NDAs
- Settlement agreements
- Protective orders
- Retainer agreements
- Any contract type

Identifies key terms, risk flags, missing clauses, and generates
redline suggestions.
"""

from __future__ import annotations

import json

import httpx

from src.config import get_settings


# ---------------------------------------------------------------------------
# Contract Type Templates — expected clauses and risk factors
# ---------------------------------------------------------------------------

CONTRACT_TEMPLATES = {
    "nda": {
        "expected_clauses": [
            "Definition of Confidential Information",
            "Obligations of Receiving Party",
            "Exclusions from Confidential Information",
            "Term and Duration",
            "Return/Destruction of Materials",
            "Remedies (injunctive relief)",
            "Governing Law",
            "Non-solicitation (if applicable)",
        ],
        "risk_factors": [
            "Overbroad definition of confidential information",
            "Perpetual duration without carve-outs",
            "One-way obligations (not mutual)",
            "No exclusions for publicly available information",
            "Liquidated damages clause",
            "Non-compete disguised as NDA",
            "Forum selection clause in unfavorable jurisdiction",
        ],
    },
    "protective_order": {
        "expected_clauses": [
            "Definition of Protected Material",
            "Confidentiality designations (Confidential, Highly Confidential, AEO)",
            "Challenge procedure for designations",
            "Permitted use restrictions",
            "Expert access provisions",
            "Clawback provisions",
            "Filing under seal procedures",
            "Return/destruction at case conclusion",
            "Survival provisions",
        ],
        "risk_factors": [
            "Overly broad AEO designation",
            "No challenge mechanism for over-designation",
            "Expert restrictions too tight for case needs",
            "No prosecution bar exception",
            "Inadequate inadvertent disclosure protections",
        ],
    },
    "settlement_agreement": {
        "expected_clauses": [
            "Recitals",
            "Settlement Amount / Consideration",
            "Payment terms and timing",
            "Tax allocation (wages vs. non-wages)",
            "General release of claims",
            "Carve-outs from release",
            "Confidentiality of settlement",
            "Non-disparagement (mutual)",
            "Neutral reference provision",
            "No rehire provision",
            "Indemnification",
            "Section 1542 waiver",
            "Attorney fees provision",
            "ADEA/OWBPA compliance (if age claim)",
            "Enforcement provisions",
            "Integration clause",
            "Governing law",
        ],
        "risk_factors": [
            "Release broader than claims in lawsuit",
            "No carve-out for future unknown claims",
            "Punitive tax allocation",
            "One-sided confidentiality",
            "No consideration period (ADEA requires 21 days)",
            "Missing 1542 waiver",
            "Vague payment terms",
            "No enforcement mechanism",
        ],
    },
    "employment_agreement": {
        "expected_clauses": [
            "Position and Duties",
            "Compensation and Benefits",
            "Term / At-will status",
            "Termination provisions",
            "Severance terms",
            "Non-compete / Non-solicitation",
            "Intellectual property assignment",
            "Confidentiality",
            "Dispute resolution (arbitration clause)",
            "Governing law",
            "Change of control provisions",
        ],
        "risk_factors": [
            "Mandatory arbitration with class waiver",
            "Overbroad non-compete (potentially void under CA law per B&P Code §16600)",
            "IP assignment covering pre-employment inventions",
            "At-will with no severance protection",
            "Unilateral modification clause",
            "Forum selection outside California",
        ],
    },
}


class ContractReviewer:
    """Analyzes contracts and generates risk assessments with redline suggestions."""

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.settings = get_settings()

    async def review_contract(
        self,
        contract_text: str,
        contract_type: str,
        case_id: str | None = None,
        org_id: str | None = None,
        reviewing_for: str = "plaintiff",
    ) -> dict:
        """
        Full contract review pipeline:
        1. AI analysis of all clauses
        2. Risk flag identification
        3. Missing clause detection
        4. Redline suggestions
        5. Overall risk score
        """
        template = CONTRACT_TEMPLATES.get(contract_type, {})

        system_prompt = f"""You are an expert California contract attorney reviewing a {contract_type.replace('_', ' ')}.
Review from the perspective of the {reviewing_for}.

{'Expected clauses: ' + json.dumps(template.get('expected_clauses', []))}
{'Known risk factors: ' + json.dumps(template.get('risk_factors', []))}

Analyze the contract and return JSON:
{{
    "summary": "2-3 paragraph executive summary",
    "key_terms": [
        {{
            "term": "term name",
            "clause_number": "section reference",
            "content": "brief description of what this clause says",
            "favorable": true/false (from {reviewing_for}'s perspective),
            "risk_level": "low" | "medium" | "high",
            "recommendation": "suggested action"
        }}
    ],
    "risk_flags": [
        {{
            "flag": "description of risk",
            "severity": "low" | "medium" | "high" | "critical",
            "clause": "section reference",
            "recommendation": "how to address"
        }}
    ],
    "missing_clauses": [
        {{
            "clause": "missing clause name",
            "importance": "required" | "recommended" | "optional",
            "recommended_language": "suggested language to add"
        }}
    ],
    "redline_suggestions": [
        {{
            "original_text": "current contract language",
            "suggested_text": "recommended replacement",
            "reason": "why this change is needed"
        }}
    ],
    "overall_risk": "low" | "medium" | "high" | "critical",
    "recommendation": "approve" | "revise" | "reject" | "negotiate",
    "california_specific_issues": ["list of CA-law-specific concerns"],
    "negotiation_priorities": ["ordered list of most important negotiation points"]
}}
Return ONLY valid JSON."""

        user_message = f"Review this {contract_type.replace('_', ' ')}:\n\n{contract_text}"

        text = await self._call_ai(system_prompt, user_message)

        try:
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {
                "summary": text,
                "key_terms": [],
                "risk_flags": [],
                "missing_clauses": [],
                "redline_suggestions": [],
                "overall_risk": "unknown",
                "recommendation": "needs_review",
            }

        # Save to database
        review_id = None
        if self.db and org_id:
            record = {
                "case_id": case_id,
                "org_id": org_id,
                "contract_type": contract_type,
                "title": f"{contract_type.replace('_', ' ').title()} Review",
                "ai_summary": analysis.get("summary", ""),
                "key_terms": json.dumps(analysis.get("key_terms", [])),
                "risk_flags": json.dumps(analysis.get("risk_flags", [])),
                "missing_clauses": json.dumps(analysis.get("missing_clauses", [])),
                "redline_suggestions": json.dumps(analysis.get("redline_suggestions", [])),
                "overall_risk": analysis.get("overall_risk", "unknown"),
                "recommendation": analysis.get("recommendation", "needs_review"),
                "status": "pending",
            }
            result = self.db.table("contract_reviews").insert(record).execute()
            review_id = result.data[0]["id"] if result.data else None

        analysis["review_id"] = review_id
        return analysis

    async def generate_contract(
        self,
        contract_type: str,
        parameters: dict,
        org_id: str | None = None,
    ) -> dict:
        """Generate a new contract from parameters."""
        system_prompt = f"""You are an expert California attorney drafting a {contract_type.replace('_', ' ')}.

Draft a complete, professional contract using proper legal formatting.
Include all standard provisions expected for this contract type.
Apply California law where applicable (especially B&P Code §16600 for non-competes,
Civil Code §1542 for releases, etc.).

Return the full contract text in markdown format with proper section numbering."""

        user_message = f"Draft a {contract_type.replace('_', ' ')} with these parameters:\n{json.dumps(parameters, indent=2)}"
        text = await self._call_ai(system_prompt, user_message)

        return {
            "contract_type": contract_type,
            "body": text,
            "parameters": parameters,
        }

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
