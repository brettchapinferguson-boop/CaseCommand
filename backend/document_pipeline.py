"""
Document Processing Pipeline
Upload → Extract Text → AI Analysis → Case Creation/Update
This is the core fix for the upload bug.
"""

import json
import fitz  # PyMuPDF
import anthropic
from typing import Optional
from config import get_settings
from database import CaseDB

_settings = None
_client = None
_db = None

def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=_get_settings().anthropic_api_key)
    return _client

def _get_db():
    global _db
    if _db is None:
        _db = CaseDB()
    return _db


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    """Extract text and metadata from PDF bytes"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    full_text = ""
    
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text})
        full_text += f"\n--- Page {i + 1} ---\n{text}"
    
    return {
        "full_text": full_text.strip(),
        "pages": pages,
        "page_count": len(doc),
        "metadata": doc.metadata
    }


def classify_document(text: str) -> dict:
    """Use Claude to classify the document type and extract key metadata"""
    response = _get_client().messages.create(
        model=_get_settings().default_model,
        max_tokens=2000,
        system="""You are a litigation document classifier. Analyze the document and return a JSON object with:
{
  "doc_type": "complaint|answer|motion|deposition|exhibit|brief|correspondence|discovery|declaration|order|other",
  "doc_subtype": "more specific type, e.g. trial_brief, msj, interrogatories, demand_letter",
  "case_name": "extracted case name if visible, e.g. 'Ruiz v. Zeller'",
  "case_number": "court case number if visible",
  "court": "court name if visible",
  "judge": "judge name if visible",
  "parties": {
    "plaintiff": ["name1"],
    "defendant": ["name2"],
    "other": []
  },
  "filing_date": "YYYY-MM-DD if visible, null otherwise",
  "summary": "2-3 sentence summary of what this document is"
}
Return ONLY valid JSON, no markdown.""",
        messages=[{"role": "user", "content": f"Classify this legal document:\n\n{text[:15000]}"}]
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        text_content = response.content[0].text
        start = text_content.find("{")
        end = text_content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text_content[start:end])
        return {"doc_type": "other", "doc_subtype": "unknown", "summary": "Could not classify document"}


def analyze_document_for_case(text: str, doc_classification: dict) -> dict:
    """Deep AI analysis: extract facts, issues, timeline, strengths/weaknesses"""
    response = _get_client().messages.create(
        model=_get_settings().default_model,
        max_tokens=4000,
        system="""You are an expert litigation analyst. Analyze this legal document thoroughly and return a JSON object:
{
  "key_facts": [
    {"fact": "description", "type": "admission|testimony|evidence|allegation|undisputed", "category": "liability|damages|credibility|timeline|procedural", "source_page": 1, "confidence": 0.9}
  ],
  "causes_of_action": [
    {"name": "Wrongful Termination", "statute": "CA Lab. Code § 1102.5", "elements": ["protected activity", "adverse action", "causal connection"], "strength": "strong|moderate|weak"}
  ],
  "key_issues": ["issue1", "issue2"],
  "strengths": ["strength1"],
  "weaknesses": ["weakness1"],
  "timeline_events": [
    {"date": "YYYY-MM-DD", "title": "Event title", "description": "What happened", "type": "filing|hearing|deposition|deadline|discovery|settlement|incident|other"}
  ],
  "legal_issues": ["employment discrimination", "retaliation"],
  "dates_mentioned": [{"date": "YYYY-MM-DD", "context": "what this date relates to"}],
  "parties_mentioned": [{"name": "John Doe", "role": "plaintiff|defendant|witness|expert|attorney"}],
  "case_summary": "Comprehensive 3-5 sentence case summary based on this document"
}
Extract as many facts and timeline events as possible. Be thorough.
Return ONLY valid JSON, no markdown.""",
        messages=[{"role": "user", "content": f"Document type: {doc_classification.get('doc_type', 'unknown')}\n\nFull text:\n\n{text[:30000]}"}]
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        text_content = response.content[0].text
        start = text_content.find("{")
        end = text_content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text_content[start:end])
        return {"key_facts": [], "causes_of_action": [], "key_issues": [], "strengths": [], "weaknesses": [], "timeline_events": [], "case_summary": "Analysis failed"}


def process_document_for_new_case(doc_id: str, user_id: str) -> dict:
    """
    Full pipeline: Process uploaded document and create a new case.
    Returns the created case and document records.
    """
    db = _get_db()
    # 1. Get document record
    doc_record = db.get_document(doc_id)
    if not doc_record:
        raise ValueError(f"Document {doc_id} not found")
    
    # Update status
    db.update_document(doc_id, {"processing_status": "processing"})
    
    try:
        # 2. Get file from storage and extract text
        file_url = db.get_file_url(doc_record["file_path"])
        
        # For now, use the extracted_text if already present (uploaded via API)
        extracted = doc_record.get("extracted_text", "")
        page_count = doc_record.get("page_count", 0)
        
        if not extracted:
            # Would download and extract - for initial version, text comes from upload
            db.update_document(doc_id, {"processing_status": "failed", "processing_error": "No text extracted"})
            raise ValueError("No extracted text available")
        
        # 3. Classify document
        classification = classify_document(extracted)
        
        # 4. Deep analysis
        analysis = analyze_document_for_case(extracted, classification)
        
        # 5. Create the case
        case_name = classification.get("case_name", "New Case")
        if not case_name or case_name == "null":
            case_name = f"Case from {doc_record['filename']}"
        
        parties = classification.get("parties", {})
        
        case_data = {
            "user_id": user_id,
            "name": case_name,
            "case_number": classification.get("case_number"),
            "case_type": _infer_case_type(classification, analysis),
            "status": "active",
            "court": classification.get("court"),
            "judge": classification.get("judge"),
            "plaintiff": json.dumps(
                [{"name": p, "role": "plaintiff"} for p in parties.get("plaintiff", [])]
            ),
            "defendant": json.dumps(
                [{"name": d, "role": "defendant"} for d in parties.get("defendant", [])]
            ),
            "summary": analysis.get("case_summary", classification.get("summary", "")),
            "key_issues": json.dumps(analysis.get("key_issues", [])),
            "causes_of_action": json.dumps(analysis.get("causes_of_action", [])),
            "strengths": json.dumps(analysis.get("strengths", [])),
            "weaknesses": json.dumps(analysis.get("weaknesses", [])),
            "filing_date": classification.get("filing_date"),
        }
        
        new_case = db.create_case(user_id, case_data)
        case_id = new_case["id"]
        
        # 6. Link document to case and update with analysis
        db.update_document(doc_id, {
            "case_id": case_id,
            "doc_type": classification.get("doc_type", "other"),
            "doc_subtype": classification.get("doc_subtype"),
            "summary": classification.get("summary", ""),
            "key_facts": json.dumps(analysis.get("key_facts", [])),
            "parties_mentioned": json.dumps(analysis.get("parties_mentioned", [])),
            "dates_mentioned": json.dumps(analysis.get("dates_mentioned", [])),
            "legal_issues": json.dumps(analysis.get("legal_issues", [])),
            "processing_status": "completed"
        })
        
        # 7. Create case facts
        facts_to_insert = []
        for fact in analysis.get("key_facts", []):
            facts_to_insert.append({
                "case_id": case_id,
                "document_id": doc_id,
                "fact_text": fact.get("fact", ""),
                "fact_type": fact.get("type", "allegation"),
                "category": fact.get("category", "liability"),
                "source_page": fact.get("source_page"),
                "confidence": fact.get("confidence", 0.8)
            })
        if facts_to_insert:
            db.create_facts(facts_to_insert)
        
        # 8. Create timeline events
        events_to_insert = []
        for event in analysis.get("timeline_events", []):
            if event.get("date"):
                events_to_insert.append({
                    "case_id": case_id,
                    "document_id": doc_id,
                    "event_date": event["date"],
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "event_type": event.get("type", "other"),
                    "is_deadline": event.get("type") == "deadline",
                    "deadline_status": "upcoming" if event.get("type") == "deadline" else None
                })
        if events_to_insert:
            db.create_timeline_events(events_to_insert)
        
        # 9. Log the action
        db.log_action({
            "case_id": case_id,
            "user_id": user_id,
            "action_type": "case_created",
            "action_description": f"Created case '{case_name}' from document '{doc_record['filename']}'",
            "status": "executed",
            "execution_result": json.dumps({
                "case_id": case_id,
                "facts_extracted": len(facts_to_insert),
                "timeline_events": len(events_to_insert),
                "causes_of_action": len(analysis.get("causes_of_action", []))
            })
        })
        
        return {
            "case": new_case,
            "document": db.get_document(doc_id),
            "facts_count": len(facts_to_insert),
            "timeline_count": len(events_to_insert),
            "analysis": analysis
        }
        
    except Exception as e:
        db.update_document(doc_id, {
            "processing_status": "failed",
            "processing_error": str(e)
        })
        raise


def process_document_for_existing_case(doc_id: str, case_id: str, user_id: str) -> dict:
    """
    Process document and add to existing case, merging new facts and timeline.
    """
    db = _get_db()
    doc_record = db.get_document(doc_id)
    if not doc_record:
        raise ValueError(f"Document {doc_id} not found")
    
    db.update_document(doc_id, {"processing_status": "processing"})
    
    try:
        extracted = doc_record.get("extracted_text", "")
        if not extracted:
            raise ValueError("No extracted text available")
        
        # Get existing case for context
        existing_case = db.get_case(case_id)
        
        # Classify
        classification = classify_document(extracted)
        
        # Analyze with case context
        analysis = analyze_document_for_case(extracted, classification)
        
        # Link document to case
        db.update_document(doc_id, {
            "case_id": case_id,
            "doc_type": classification.get("doc_type", "other"),
            "doc_subtype": classification.get("doc_subtype"),
            "summary": classification.get("summary", ""),
            "key_facts": json.dumps(analysis.get("key_facts", [])),
            "parties_mentioned": json.dumps(analysis.get("parties_mentioned", [])),
            "dates_mentioned": json.dumps(analysis.get("dates_mentioned", [])),
            "legal_issues": json.dumps(analysis.get("legal_issues", [])),
            "processing_status": "completed"
        })
        
        # Add new facts
        facts_to_insert = []
        for fact in analysis.get("key_facts", []):
            facts_to_insert.append({
                "case_id": case_id,
                "document_id": doc_id,
                "fact_text": fact.get("fact", ""),
                "fact_type": fact.get("type", "allegation"),
                "category": fact.get("category", "liability"),
                "source_page": fact.get("source_page"),
                "confidence": fact.get("confidence", 0.8)
            })
        if facts_to_insert:
            db.create_facts(facts_to_insert)
        
        # Add timeline events
        events_to_insert = []
        for event in analysis.get("timeline_events", []):
            if event.get("date"):
                events_to_insert.append({
                    "case_id": case_id,
                    "document_id": doc_id,
                    "event_date": event["date"],
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "event_type": event.get("type", "other"),
                    "is_deadline": event.get("type") == "deadline",
                    "deadline_status": "upcoming" if event.get("type") == "deadline" else None
                })
        if events_to_insert:
            db.create_timeline_events(events_to_insert)
        
        # Update case summary by merging new info
        _update_case_analysis(case_id, user_id, analysis, existing_case)
        
        # Log action
        db.log_action({
            "case_id": case_id,
            "user_id": user_id,
            "action_type": "document_added",
            "action_description": f"Added '{doc_record['filename']}' to case '{existing_case['name']}'",
            "status": "executed",
            "execution_result": json.dumps({
                "document_id": doc_id,
                "new_facts": len(facts_to_insert),
                "new_timeline_events": len(events_to_insert)
            })
        })
        
        return {
            "case": db.get_case(case_id),
            "document": db.get_document(doc_id),
            "new_facts_count": len(facts_to_insert),
            "new_timeline_count": len(events_to_insert)
        }
        
    except Exception as e:
        db.update_document(doc_id, {
            "processing_status": "failed",
            "processing_error": str(e)
        })
        raise


def _update_case_analysis(case_id: str, user_id: str, new_analysis: dict, existing_case: dict):
    """Merge new document analysis into existing case"""
    db = _get_db()
    # Merge key issues
    existing_issues = existing_case.get("key_issues") or []
    if isinstance(existing_issues, str):
        existing_issues = json.loads(existing_issues)
    new_issues = list(set(existing_issues + (new_analysis.get("key_issues") or [])))
    
    # Merge causes of action  
    existing_coa = existing_case.get("causes_of_action") or []
    if isinstance(existing_coa, str):
        existing_coa = json.loads(existing_coa)
    new_coa_names = {c.get("name") for c in existing_coa}
    for coa in new_analysis.get("causes_of_action", []):
        if coa.get("name") not in new_coa_names:
            existing_coa.append(coa)
    
    # Update case with merged analysis
    update_data = {
        "key_issues": json.dumps(new_issues),
        "causes_of_action": json.dumps(existing_coa),
    }
    
    # Regenerate summary with all info
    if new_analysis.get("case_summary"):
        existing_summary = existing_case.get("summary", "")
        response = _get_client().messages.create(
            model=_get_settings().default_model,
            max_tokens=500,
            messages=[{"role": "user", "content": f"""Merge these two case summaries into one comprehensive summary (3-5 sentences):

Existing summary: {existing_summary}

New information: {new_analysis['case_summary']}

Return only the merged summary, no other text."""}]
        )
        update_data["summary"] = response.content[0].text.strip()
    
    db.update_case(case_id, update_data)


def _infer_case_type(classification: dict, analysis: dict) -> str:
    """Infer case type from classification and analysis"""
    legal_issues = analysis.get("legal_issues", [])
    doc_type = classification.get("doc_type", "")
    summary = classification.get("summary", "").lower()
    
    keywords = {
        "employment": ["employment", "wrongful termination", "discrimination", "harassment", "retaliation", "wage", "feha", "title vii", "flsa"],
        "personal_injury": ["personal injury", "negligence", "accident", "damages", "medical", "liability"],
        "civil_rights": ["civil rights", "1983", "constitutional", "first amendment", "due process"],
        "family": ["custody", "divorce", "child support", "visitation", "family"],
        "business": ["breach of contract", "business", "commercial", "partnership", "corporate"],
    }
    
    all_text = " ".join(legal_issues + [summary]).lower()
    
    for case_type, kws in keywords.items():
        if any(kw in all_text for kw in kws):
            return case_type
    
    return "civil"
