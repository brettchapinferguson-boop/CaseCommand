"""
CaseCommand AI — Claude API Integration Layer
Agentic orchestrator using async httpx and native tool use.
"""

import os
import json
from pathlib import Path

import httpx


def _load_env():
    """Load .env from project root into os.environ (only sets missing vars)."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()


class CaseCommandAI:
    """Claude-powered legal analysis client."""

    MODEL = "claude-sonnet-4-6"
    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )
        self._headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # ------------------------------------------------------------------
        # Agent tool definitions
        # ------------------------------------------------------------------
        self.tools = [
            {
                "name": "generate_legal_document",
                "description": (
                    "Draft a substantive legal document (e.g., Meet and Confer letter, "
                    "motion, pleading, settlement agreement, demand letter). Use this "
                    "whenever the user asks to draft, write, or generate a document. "
                    "Returns structured JSON with title and body so the system can "
                    "compile a downloadable .docx file."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short descriptive filename, e.g., Meet_and_Confer_Smith_v_Jones",
                        },
                        "body": {
                            "type": "string",
                            "description": (
                                "The fully formatted text of the legal document. "
                                "Use markdown for headers (###) and bolding (**text**)."
                            ),
                        },
                    },
                    "required": ["title", "body"],
                },
            }
        ]

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_proxy() -> str | None:
        _env_proxy = (
            os.environ.get("HTTPS_PROXY")
            or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("http_proxy")
        )
        return _env_proxy if _env_proxy and not _env_proxy.startswith("socks") else None

    def _call_api(self, system_prompt: str, user_message: str, max_tokens: int = 2048) -> dict:
        """Synchronous POST — kept for non-chat endpoints (discovery, outline, settlement)."""
        payload = {
            "model": self.MODEL,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        with httpx.Client(timeout=90.0, trust_env=False, proxy=self._get_proxy()) as client:
            response = client.post(
                f"{self.BASE_URL}/messages",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "text": data["content"][0]["text"],
            "model": data["model"],
            "usage": data.get("usage", {}),
        }

    async def _call_api_async(
        self, system_prompt: str, messages: list, max_tokens: int = 4096
    ) -> dict:
        """Async POST with tool-use support — used by the agent loop."""
        payload = {
            "model": self.MODEL,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
            "tools": self.tools,
        }
        async with httpx.AsyncClient(
            timeout=120.0, trust_env=False, proxy=self._get_proxy()
        ) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Agent loop — routes between plain chat and tool calls
    # ------------------------------------------------------------------

    async def chat_agent_loop(
        self, user_message: str, active_cases_context: str = ""
    ) -> dict:
        """
        Master agent router. Sends the user message to Claude, checks
        whether it wants to reply normally or invoke a tool, and returns
        a dict with 'reply', 'tool_calls', and 'model'.
        """
        system_prompt = (
            "You are Casey, the lead litigation assistant for CaseCommand. "
            "You act as an expert trial attorney and elite paralegal. "
            "You manage case files, draft precise legal documents (applying "
            "strict formatting rules, particularly for California state court "
            "and FEHA matters where applicable), and assist with litigation strategy.\n"
            "If the user asks you to draft a document, you MUST use the "
            "`generate_legal_document` tool. Do NOT output raw document text "
            "in your standard reply when using the tool.\n\n"
            f"Active Cases Context:\n{active_cases_context}"
        )

        messages = [{"role": "user", "content": user_message}]
        data = await self._call_api_async(system_prompt, messages)

        content_blocks = data.get("content", [])
        response_dict: dict = {
            "reply": "",
            "tool_calls": [],
            "model": data.get("model", self.MODEL),
        }

        for block in content_blocks:
            if block["type"] == "text":
                response_dict["reply"] += block["text"] + "\n"
            elif block["type"] == "tool_use":
                response_dict["tool_calls"].append(
                    {"id": block["id"], "name": block["name"], "input": block["input"]}
                )

        return response_dict

    # ------------------------------------------------------------------
    # DisputeFlow — Discovery Analysis
    # ------------------------------------------------------------------

    def analyze_discovery_responses(
        self,
        case_name: str,
        discovery_type: str,
        requests_and_responses: list,
    ) -> dict:
        """
        Analyze interrogatories, RFPs, or RFAs and surface strategic insights.

        Args:
            case_name: Human-readable case identifier.
            discovery_type: e.g. "interrogatories", "requests for production".
            requests_and_responses: List of dicts with keys "number", "request", "response".

        Returns:
            dict with keys: text, model, usage.
        """
        system_prompt = (
            "You are CaseCommand AI, an expert litigation analyst. "
            "Analyze discovery responses and deliver concise, actionable findings "
            "for trial preparation. Focus on admissions, evasions, inconsistencies, "
            "and strategic opportunities."
        )

        formatted_qa = "\n\n".join(
            f"Request {item['number']}:\n{item['request']}\n\nResponse:\n{item['response']}"
            for item in requests_and_responses
        )

        user_message = f"""Case: {case_name}
Discovery Type: {discovery_type}

--- Discovery Requests & Responses ---
{formatted_qa}

Please provide:
1. Key findings and admissions
2. Evasive or incomplete responses requiring follow-up
3. Inconsistencies or contradictions to exploit at trial
4. Strategic opportunities
5. Recommended follow-up discovery"""

        return self._call_api(system_prompt, user_message)

    # ------------------------------------------------------------------
    # TrialPrep — Examination Outline (synchronous — called by dedicated endpoints)
    # ------------------------------------------------------------------

    def generate_examination_outline(
        self,
        case_name: str,
        witness_name: str,
        witness_role: str,
        exam_type: str,
        case_documents: list,
        case_theory: str,
    ) -> dict:
        """
        Generate a direct- or cross-examination outline for a witness.

        Args:
            case_name: Human-readable case identifier.
            witness_name: Full name of the witness.
            witness_role: e.g. "plaintiff", "defendant", "expert", "eyewitness".
            exam_type: "direct" or "cross".
            case_documents: List of document descriptions or dicts to anchor questions.
            case_theory: One-sentence theme the examination must support.

        Returns:
            dict with keys: text, model, usage.
        """
        system_prompt = (
            "You are CaseCommand AI, an expert trial attorney. "
            "Create structured, strategically sequenced examination outlines. "
            "Each section should have a clear goal and suggest specific questions."
        )

        docs_text = (
            "\n".join(f"- {doc}" for doc in case_documents)
            if case_documents
            else "No documents provided."
        )

        user_message = f"""Case: {case_name}
Witness: {witness_name} ({witness_role})
Examination Type: {exam_type.upper()}
Case Theory: {case_theory}

Supporting Documents / Facts:
{docs_text}

Generate a comprehensive {exam_type}-examination outline that:
1. Opens strategically
2. Covers all key factual areas
3. Establishes or challenges credibility
4. Advances the case theory: "{case_theory}"
5. Closes with maximum impact"""

        return self._call_api(system_prompt, user_message)

    # ------------------------------------------------------------------
    # Settlement — Narrative & Assessment
    # ------------------------------------------------------------------

    def generate_settlement_narrative(
        self,
        case_name: str,
        trigger_point: str,
        valuation_data: dict,
        recommendation_data: dict,
    ) -> dict:
        """
        Produce a settlement assessment memo with negotiation strategy.

        Args:
            case_name: Human-readable case identifier.
            trigger_point: Stage at which settlement is being considered,
                           e.g. "Post-Discovery", "Pre-Trial", "During Trial".
            valuation_data: Dict with keys low, mid, high (numeric dollar amounts).
            recommendation_data: Arbitrary dict of supporting factors
                                  (liability_strength, damages_proven, etc.).

        Returns:
            dict with keys: text, model, usage.
        """
        system_prompt = (
            "You are CaseCommand AI, an expert in litigation risk and settlement strategy. "
            "Provide objective, data-driven settlement assessments that help attorneys "
            "advise clients and drive successful negotiations."
        )

        low = valuation_data.get("low", 0)
        mid = valuation_data.get("mid", 0)
        high = valuation_data.get("high", 0)

        user_message = f"""Case: {case_name}
Settlement Trigger: {trigger_point}

Valuation Range:
  Low:  ${low:,}
  Mid:  ${mid:,}
  High: ${high:,}

Supporting Data:
{json.dumps(recommendation_data, indent=2)}

Generate a comprehensive settlement assessment covering:
1. Case strength and liability analysis
2. Key risk factors for both sides
3. Settlement recommendation with rationale
4. Negotiation strategy and opening position
5. Timeline and leverage considerations"""

        return self._call_api(system_prompt, user_message)
