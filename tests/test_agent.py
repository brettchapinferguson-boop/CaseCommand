"""Tests for the agentic loop."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

import agent
import database as db


@pytest.fixture
def fresh_db(tmp_path):
    db.DB_PATH = str(tmp_path / "agent_test.db")
    asyncio.run(db.init_db())
    yield


def _text_response(text):
    return {
        "success": True,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 20},
        "error": None,
    }


def _tool_response(tool_name, tool_input, tool_id="tu_1"):
    return {
        "success": True,
        "content": [
            {"type": "text", "text": "Working on it."},
            {"type": "tool_use", "id": tool_id, "name": tool_name, "input": tool_input},
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 100, "output_tokens": 30},
        "error": None,
    }


def test_agent_returns_text_when_no_tools_needed(fresh_db):
    with patch("claude_client.call_claude_raw", new_callable=AsyncMock,
               return_value=_text_response("All caught up.")):
        result = asyncio.run(agent.run_agent(
            "system", [{"role": "user", "content": "status?"}]
        ))
    assert result["success"] is True
    assert result["text"] == "All caught up."
    assert result["actions"] == []


def test_agent_executes_tool_then_finishes(fresh_db):
    responses = [
        _tool_response("create_task", {"title": "Draft M&C letter", "case_id": "c1"}),
        _text_response("Created the task."),
    ]
    with patch("claude_client.call_claude_raw", new_callable=AsyncMock,
               side_effect=responses):
        result = asyncio.run(agent.run_agent(
            "system", [{"role": "user", "content": "make a task"}],
            actor="agent:test",
        ))
    assert result["success"] is True
    assert result["text"] == "Created the task."
    assert len(result["actions"]) == 1
    assert result["actions"][0].startswith("create_task")
    # The tool actually executed against the database
    task_list = asyncio.run(db.list_tasks(status="open"))
    assert any(t["title"] == "Draft M&C letter" for t in task_list)


def test_agent_accumulates_usage(fresh_db):
    responses = [
        _tool_response("list_cases", {}),
        _text_response("3 cases active."),
    ]
    with patch("claude_client.call_claude_raw", new_callable=AsyncMock,
               side_effect=responses):
        result = asyncio.run(agent.run_agent(
            "system", [{"role": "user", "content": "how many cases?"}]
        ))
    assert result["usage"]["input_tokens"] == 200
    assert result["usage"]["output_tokens"] == 50


def test_agent_iteration_cap(fresh_db):
    # Model that never stops calling tools
    looping = _tool_response("list_cases", {})
    final = _text_response("Summary of work done.")

    call_count = {"n": 0}

    async def fake_call(*args, **kwargs):
        call_count["n"] += 1
        # After the cap, run_agent sends a no-tools summary request
        if kwargs.get("tools") is None and call_count["n"] > 3:
            return final
        return looping if kwargs.get("tools") else final

    with patch("claude_client.call_claude_raw", new_callable=AsyncMock,
               side_effect=fake_call):
        result = asyncio.run(agent.run_agent(
            "system", [{"role": "user", "content": "go"}], max_iterations=3
        ))
    assert result["success"] is True
    assert len(result["actions"]) == 3  # capped
    assert result["text"] == "Summary of work done."


def test_agent_propagates_api_failure(fresh_db):
    failure = {"success": False, "content": [], "stop_reason": None,
               "usage": {}, "error": "AI service timeout"}
    with patch("claude_client.call_claude_raw", new_callable=AsyncMock,
               return_value=failure):
        result = asyncio.run(agent.run_agent(
            "system", [{"role": "user", "content": "hi"}]
        ))
    assert result["success"] is False
    assert result["error"] == "AI service timeout"


def test_commander_prompt_includes_ethics(fresh_db):
    prompt = asyncio.run(agent.build_commander_prompt())
    assert "RPC 5.3" in prompt
    assert "CANNOT send, serve, file" in prompt
    assert "Rodriguez v. Smith Trucking" in prompt


def test_paralegal_prompt_includes_workload(fresh_db):
    prompt = asyncio.run(agent.build_paralegal_prompt())
    assert "autonomous AI paralegal" in prompt
    assert "PENDING DEADLINES" in prompt
    assert "RPC 5.3" in prompt
