"""
Agentic Chat Engine
The chatbot that can take actions, not just answer questions.
Uses Claude's function calling to interact with the system.
"""

import json
import anthropic
from typing import Optional
from config import get_settings
from database import CaseDB
from document_pipeline import process_document_for_new_case, process_document_for_existing_case

_settings = None
_ai_client = None
_db = None

def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings

def _get_ai_client():
    global _ai_client
    if _ai_client is None:
        _ai_client = anthropic.Anthropic(api_key=_get_settings().anthropic_api_key)
    return _ai_client

def _get_db():
    global _db
    if _db is None:
        _db = CaseDB()
    return _db


# ── Tool Definitions ──────────────────────────────────────────

TOOLS = [
    {
        "name": "create_case_from_document",
        "description": "Create a new case in the dashboard from an uploaded document. Triggers the full document processing pipeline: text extraction, AI analysis, fact extraction, timeline generation, and case creation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "The UUID of the uploaded document to process"
                }
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "add_document_to_case",
        "description": "Add an uploaded document to an existing case. Processes the document and merges new facts and timeline events into the case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "The UUID of the uploaded document"
                },
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the existing case to add the document to"
                }
            },
            "required": ["document_id", "case_id"]
        }
    },
    {
        "name": "list_cases",
        "description": "List all cases in the dashboard. Use this when the user asks about their cases or needs to find a specific case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "discovery", "trial_prep", "trial", "settled", "closed", "archived"],
                    "description": "Optional filter by case status"
                }
            }
        }
    },
    {
        "name": "get_case_details",
        "description": "Get full details of a specific case including summary, key issues, causes of action, facts, timeline, and documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the case"
                }
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "get_case_facts",
        "description": "Get all extracted facts for a case, optionally filtered by category (liability, damages, credibility, timeline, procedural).",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the case"
                },
                "category": {
                    "type": "string",
                    "enum": ["liability", "damages", "credibility", "timeline", "procedural"],
                    "description": "Optional category filter"
                }
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "get_case_timeline",
        "description": "Get the chronological timeline of events for a case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the case"
                }
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "generate_document",
        "description": "Generate a litigation document using AI. Types include: cross_exam_outline, direct_exam_outline, motion, demand_letter, meet_and_confer, discovery_requests, discovery_responses, trial_brief, settlement_analysis, case_summary, deposition_outline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the case"
                },
                "document_type": {
                    "type": "string",
                    "description": "Type of document to generate"
                },
                "instructions": {
                    "type": "string",
                    "description": "Specific instructions for the document, e.g., 'Focus on the retaliation claim' or 'Cross-examination outline for Dr. Williams'"
                }
            },
            "required": ["case_id", "document_type"]
        }
    },
    {
        "name": "propose_calendar_event",
        "description": "Propose creating a calendar event. This creates a pending action that requires user approval before being added to Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the related case (optional)"
                },
                "title": {
                    "type": "string",
                    "description": "Event title"
                },
                "date": {
                    "type": "string",
                    "description": "Event date in YYYY-MM-DD format"
                },
                "time": {
                    "type": "string",
                    "description": "Event time in HH:MM format (24hr)"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes, default 60"
                },
                "location": {
                    "type": "string",
                    "description": "Event location"
                },
                "description": {
                    "type": "string",
                    "description": "Event description/notes"
                }
            },
            "required": ["title", "date"]
        }
    },
    {
        "name": "propose_email",
        "description": "Propose sending an email. Creates a pending action with the draft email for user approval before sending via Gmail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the related case (optional)"
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body text"
                },
                "cc": {
                    "type": "string",
                    "description": "CC email addresses (comma-separated)"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "update_case_status",
        "description": "Update the status of a case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "The UUID of the case"
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "discovery", "trial_prep", "trial", "settled", "closed", "archived"],
                    "description": "New status"
                }
            },
            "required": ["case_id", "status"]
        }
    },
    {
        "name": "search_recent_uploads",
        "description": "Find recently uploaded documents that haven't been assigned to a case yet.",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    }
]


# ── Tool Execution ────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict, user_id: str) -> str:
    """Execute a tool call and return the result as a string"""
    db = _get_db()
    settings = _get_settings()
    ai_client = _get_ai_client()

    try:
        if tool_name == "create_case_from_document":
            result = process_document_for_new_case(tool_input["document_id"], user_id)
            case = result["case"]
            return json.dumps({
                "success": True,
                "message": f"Case '{case['name']}' created successfully",
                "case_id": case["id"],
                "case_name": case["name"],
                "facts_extracted": result["facts_count"],
                "timeline_events": result["timeline_count"],
                "summary": case.get("summary", ""),
                "causes_of_action": json.loads(case.get("causes_of_action", "[]")) if isinstance(case.get("causes_of_action"), str) else case.get("causes_of_action", [])
            })
        
        elif tool_name == "add_document_to_case":
            result = process_document_for_existing_case(
                tool_input["document_id"], tool_input["case_id"], user_id
            )
            return json.dumps({
                "success": True,
                "message": f"Document added to case '{result['case']['name']}'",
                "new_facts": result["new_facts_count"],
                "new_timeline_events": result["new_timeline_count"]
            })
        
        elif tool_name == "list_cases":
            cases = db.get_cases(user_id, tool_input.get("status"))
            return json.dumps({
                "success": True,
                "cases": [{
                    "id": c["id"],
                    "name": c["name"],
                    "case_type": c.get("case_type"),
                    "status": c.get("status"),
                    "summary": c.get("summary", "")[:200],
                    "updated_at": c.get("updated_at")
                } for c in cases]
            })
        
        elif tool_name == "get_case_details":
            case = db.get_case(tool_input["case_id"])
            docs = db.get_documents(tool_input["case_id"])
            facts = db.get_facts(tool_input["case_id"])
            timeline = db.get_timeline(tool_input["case_id"])
            return json.dumps({
                "success": True,
                "case": case,
                "documents": [{"id": d["id"], "filename": d["filename"], "doc_type": d.get("doc_type"), "summary": d.get("summary")} for d in docs],
                "facts_count": len(facts),
                "timeline_events_count": len(timeline)
            }, default=str)
        
        elif tool_name == "get_case_facts":
            facts = db.get_facts(tool_input["case_id"], tool_input.get("category"))
            return json.dumps({"success": True, "facts": facts}, default=str)
        
        elif tool_name == "get_case_timeline":
            timeline = db.get_timeline(tool_input["case_id"])
            return json.dumps({"success": True, "timeline": timeline}, default=str)
        
        elif tool_name == "generate_document":
            # Get case context
            case = db.get_case(tool_input["case_id"])
            facts = db.get_facts(tool_input["case_id"])
            doc_type = tool_input["document_type"]
            instructions = tool_input.get("instructions", "")
            
            # Build context for generation
            context = f"Case: {case['name']}\nSummary: {case.get('summary', '')}\n"
            context += f"Key Issues: {json.dumps(case.get('key_issues', []))}\n"
            context += f"Causes of Action: {json.dumps(case.get('causes_of_action', []))}\n\n"
            context += "Key Facts:\n"
            for f in facts[:30]:
                context += f"- [{f.get('category', '')}] {f['fact_text']}\n"
            
            response = ai_client.messages.create(
                model=settings.default_model,
                max_tokens=4000,
                system=f"You are an expert litigation attorney generating a {doc_type}. Use the case facts and context provided. Be thorough and professional.",
                messages=[{"role": "user", "content": f"{context}\n\nGenerate a {doc_type}. {instructions}"}]
            )
            
            generated_text = response.content[0].text
            return json.dumps({
                "success": True,
                "document_type": doc_type,
                "content": generated_text,
                "message": f"Generated {doc_type} for {case['name']}"
            })
        
        elif tool_name == "propose_calendar_event":
            action = db.log_action({
                "case_id": tool_input.get("case_id"),
                "user_id": user_id,
                "action_type": "calendar_created",
                "action_description": f"Create calendar event: {tool_input['title']} on {tool_input['date']}",
                "action_payload": json.dumps(tool_input),
                "status": "pending"
            })
            return json.dumps({
                "success": True,
                "message": f"Calendar event proposed: '{tool_input['title']}' on {tool_input['date']}. Awaiting your approval.",
                "action_id": action["id"],
                "requires_approval": True
            })
        
        elif tool_name == "propose_email":
            action = db.log_action({
                "case_id": tool_input.get("case_id"),
                "user_id": user_id,
                "action_type": "email_sent",
                "action_description": f"Send email to {tool_input['to']}: {tool_input['subject']}",
                "action_payload": json.dumps(tool_input),
                "status": "pending"
            })
            return json.dumps({
                "success": True,
                "message": f"Email draft created to {tool_input['to']}. Subject: '{tool_input['subject']}'. Awaiting your approval.",
                "action_id": action["id"],
                "requires_approval": True
            })
        
        elif tool_name == "update_case_status":
            db.update_case(tool_input["case_id"], {"status": tool_input["status"]})
            return json.dumps({
                "success": True,
                "message": f"Case status updated to '{tool_input['status']}'"
            })
        
        elif tool_name == "search_recent_uploads":
            docs = db.get_pending_documents()
            # Filter to user's docs
            user_docs = [d for d in docs if d.get("user_id") == user_id]
            return json.dumps({
                "success": True,
                "unassigned_documents": [{
                    "id": d["id"],
                    "filename": d["filename"],
                    "uploaded_at": d.get("created_at"),
                    "processing_status": d.get("processing_status")
                } for d in user_docs]
            }, default=str)
        
        else:
            return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Chat Engine ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are CaseCommand, an AI litigation operating system. You are an agentic assistant that can take real actions, not just answer questions.

You have access to tools that let you:
- Create new cases from uploaded documents
- Add documents to existing cases
- List and search cases
- Get case details, facts, and timelines
- Generate litigation documents (cross-exam outlines, motions, letters, etc.)
- Propose calendar events (requires user approval)
- Propose emails (requires user approval)
- Update case statuses

IMPORTANT BEHAVIORS:
1. When a user mentions they uploaded a document, use search_recent_uploads to find it, then offer to create a new case or add to existing.
2. When taking external actions (calendar, email), ALWAYS create a pending action for approval. Never claim to have sent an email or created a calendar event without the approval step.
3. Be proactive - suggest next steps based on the case context.
4. Reference specific case facts when discussing strategy.
5. Maintain awareness of which case is currently active in the conversation.

You are built for Brett Ferguson, an experienced California litigator. Match his expertise level - be precise, strategic, and efficient. Don't over-explain basic legal concepts."""


def chat(user_message: str, user_id: str, session_id: str, case_id: Optional[str] = None) -> dict:
    """
    Main chat function. Handles multi-turn conversation with function calling.
    Returns the assistant's response and any actions taken.
    """
    db = _get_db()
    settings = _get_settings()
    ai_client = _get_ai_client()

    # Get conversation history
    history = db.get_conversation(session_id, limit=20)

    # Build messages
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add case context if active
    system = SYSTEM_PROMPT
    if case_id:
        try:
            case = db.get_case(case_id)
            if case:
                system += f"\n\nACTIVE CASE: {case['name']} (ID: {case['id']})"
                system += f"\nType: {case.get('case_type', 'Unknown')}"
                system += f"\nStatus: {case.get('status', 'active')}"
                system += f"\nSummary: {case.get('summary', 'No summary yet')}"
        except Exception:
            pass
    
    messages.append({"role": "user", "content": user_message})
    
    # Save user message
    db.save_message({
        "user_id": user_id,
        "session_id": session_id,
        "case_id": case_id,
        "role": "user",
        "content": user_message
    })
    
    # Call Claude with tools
    actions_taken = []
    max_iterations = 5  # prevent infinite loops
    
    for _ in range(max_iterations):
        response = ai_client.messages.create(
            model=settings.default_model,
            max_tokens=4000,
            system=system,
            tools=TOOLS,
            messages=messages
        )
        
        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process tool calls
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})
            
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input, user_id)
                    actions_taken.append({
                        "tool": block.name,
                        "input": block.input,
                        "result": json.loads(result)
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            messages.append({"role": "user", "content": tool_results})
            continue
        
        # Final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text
        
        # Save assistant response
        db.save_message({
            "user_id": user_id,
            "session_id": session_id,
            "case_id": case_id,
            "role": "assistant",
            "content": final_text,
            "tool_calls": json.dumps(actions_taken) if actions_taken else None,
            "model": settings.default_model
        })
        
        return {
            "response": final_text,
            "actions": actions_taken,
            "session_id": session_id
        }
    
    # Fallback if max iterations reached
    return {
        "response": "I've completed several actions. Let me know if you need anything else.",
        "actions": actions_taken,
        "session_id": session_id
    }
