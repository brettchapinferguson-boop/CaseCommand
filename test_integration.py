#!/usr/bin/env python3
"""
CaseCommand — Integration Test Suite
Verifies environment, API connectivity, and all three AI features.

Usage:
    python3 test_integration.py
"""

import os
import sys
from pathlib import Path


def _load_env():
    """Load .env from the project root before any checks run."""
    env_path = Path(__file__).parent / ".env"
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


# ------------------------------------------------------------------ #
# Pre-flight checks (env file + API key)                              #
# ------------------------------------------------------------------ #

def check_env_file() -> bool:
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        print("  ✓ .env file found")
        return True
    print("  ✗ .env file not found — copy .env.example to .env and fill in your keys")
    return False


def check_api_key() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and key.startswith("sk-ant-"):
        print("  ✓ ANTHROPIC_API_KEY: configured")
        return True
    print("  ✗ ANTHROPIC_API_KEY: not set or invalid format")
    return False


# ------------------------------------------------------------------ #
# Feature tests                                                       #
# ------------------------------------------------------------------ #

def test_connection(ai) -> bool:
    """Ping the API and print the model name."""
    try:
        result = ai._call_api(
            system_prompt="You are a test assistant.",
            user_message="Reply with only the word READY.",
            max_tokens=10,
        )
        print(f"  ✓ API connected — model: {result['model']}")
        return True
    except Exception as exc:
        print(f"  ✗ API connection failed: {exc}")
        return False


def test_disputeflow(ai) -> bool:
    """DisputeFlow: discovery response analysis."""
    try:
        result = ai.analyze_discovery_responses(
            case_name="Smith v. Jones",
            discovery_type="interrogatories",
            requests_and_responses=[
                {
                    "number": 1,
                    "request": "State all facts supporting your claim of negligence.",
                    "response": "Defendant failed to maintain safe premises on the date in question.",
                }
            ],
        )
        if result and result.get("text"):
            print("  ✓ DisputeFlow analysis completed")
            return True
        print("  ✗ DisputeFlow analysis returned empty content")
        return False
    except Exception as exc:
        print(f"  ✗ DisputeFlow analysis failed: {exc}")
        return False


def test_trialprep(ai) -> bool:
    """TrialPrep: examination outline generation."""
    try:
        result = ai.generate_examination_outline(
            case_name="Smith v. Jones",
            witness_name="John Smith",
            witness_role="plaintiff",
            exam_type="direct",
            case_documents=["Incident report dated 2024-01-15"],
            case_theory="Defendant's negligence caused preventable injuries",
        )
        if result and result.get("text"):
            print("  ✓ TrialPrep outline generated")
            return True
        print("  ✗ TrialPrep outline returned empty content")
        return False
    except Exception as exc:
        print(f"  ✗ TrialPrep outline failed: {exc}")
        return False


def test_settlement(ai) -> bool:
    """Settlement: narrative and assessment generation."""
    try:
        result = ai.generate_settlement_narrative(
            case_name="Smith v. Jones",
            trigger_point="Post-Discovery",
            valuation_data={"low": 100000, "mid": 200000, "high": 350000},
            recommendation_data={
                "liability_strength": "strong",
                "damages_proven": True,
                "trial_risk": "moderate",
            },
        )
        if result and result.get("text"):
            print("  ✓ Settlement narrative generated")
            return True
        print("  ✗ Settlement narrative returned empty content")
        return False
    except Exception as exc:
        print(f"  ✗ Settlement narrative failed: {exc}")
        return False


# ------------------------------------------------------------------ #
# Main                                                                #
# ------------------------------------------------------------------ #

def main():
    print("\n--- CaseCommand Integration Test ---\n")

    # Pre-flight
    if not check_env_file():
        sys.exit(1)
    if not check_api_key():
        sys.exit(1)

    # Load AI client (api_client.py re-reads .env automatically)
    try:
        from src.api_client import CaseCommandAI
        ai = CaseCommandAI()
    except Exception as exc:
        print(f"  ✗ Failed to initialize CaseCommandAI: {exc}")
        sys.exit(1)

    # Connection check
    if not test_connection(ai):
        sys.exit(1)

    # Feature tests
    results = [
        test_disputeflow(ai),
        test_trialprep(ai),
        test_settlement(ai),
    ]

    passed = sum(results)
    total = len(results)

    print(f"\n  {passed}/{total} tests passed")

    if passed == total:
        print("  ✓ All systems operational. CaseCommand is ready.")
    else:
        print("  ✗ Some tests failed. Check your configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
