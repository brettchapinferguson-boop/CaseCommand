from supabase import create_client, Client
from config import get_settings
from functools import lru_cache
import json
from datetime import date, datetime
from typing import Optional
import uuid


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


@lru_cache()
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


class CaseDB:
    """Database operations for cases"""
    
    def __init__(self):
        self.client = get_supabase()
    
    # ── Cases ──────────────────────────────────────────────
    
    def create_case(self, user_id: str, data: dict) -> dict:
        data["user_id"] = user_id
        result = self.client.table("cases").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_cases(self, user_id: str, status: Optional[str] = None) -> list:
        query = self.client.table("cases").select("*").eq("user_id", user_id).order("updated_at", desc=True)
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.data or []
    
    def get_case(self, case_id: str) -> dict:
        result = self.client.table("cases").select("*").eq("id", case_id).single().execute()
        return result.data
    
    def update_case(self, case_id: str, data: dict) -> dict:
        result = self.client.table("cases").update(data).eq("id", case_id).execute()
        return result.data[0] if result.data else None
    
    # ── Documents ──────────────────────────────────────────
    
    def create_document(self, data: dict) -> dict:
        result = self.client.table("documents").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_documents(self, case_id: str) -> list:
        result = self.client.table("documents").select("*").eq("case_id", case_id).order("created_at", desc=True).execute()
        return result.data or []
    
    def get_document(self, doc_id: str) -> dict:
        result = self.client.table("documents").select("*").eq("id", doc_id).single().execute()
        return result.data
    
    def update_document(self, doc_id: str, data: dict) -> dict:
        result = self.client.table("documents").update(data).eq("id", doc_id).execute()
        return result.data[0] if result.data else None
    
    def get_pending_documents(self) -> list:
        result = self.client.table("documents").select("*").eq("processing_status", "pending").execute()
        return result.data or []
    
    # ── Case Facts ─────────────────────────────────────────
    
    def create_facts(self, facts: list[dict]) -> list:
        if not facts:
            return []
        result = self.client.table("case_facts").insert(facts).execute()
        return result.data or []
    
    def get_facts(self, case_id: str, category: Optional[str] = None) -> list:
        query = self.client.table("case_facts").select("*").eq("case_id", case_id)
        if category:
            query = query.eq("category", category)
        result = query.order("created_at").execute()
        return result.data or []
    
    # ── Timeline ───────────────────────────────────────────
    
    def create_timeline_events(self, events: list[dict]) -> list:
        if not events:
            return []
        result = self.client.table("timeline_events").insert(events).execute()
        return result.data or []
    
    def get_timeline(self, case_id: str) -> list:
        result = self.client.table("timeline_events").select("*").eq("case_id", case_id).order("event_date").execute()
        return result.data or []
    
    # ── Conversations ──────────────────────────────────────
    
    def save_message(self, data: dict) -> dict:
        result = self.client.table("conversations").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_conversation(self, session_id: str, limit: int = 50) -> list:
        result = (self.client.table("conversations")
                  .select("*")
                  .eq("session_id", session_id)
                  .order("created_at")
                  .limit(limit)
                  .execute())
        return result.data or []
    
    def get_case_conversations(self, case_id: str, limit: int = 20) -> list:
        result = (self.client.table("conversations")
                  .select("*")
                  .eq("case_id", case_id)
                  .order("created_at", desc=True)
                  .limit(limit)
                  .execute())
        return result.data or []
    
    # ── Action Log ─────────────────────────────────────────
    
    def log_action(self, data: dict) -> dict:
        result = self.client.table("action_log").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_pending_actions(self, user_id: str) -> list:
        result = (self.client.table("action_log")
                  .select("*")
                  .eq("user_id", user_id)
                  .eq("status", "pending")
                  .order("created_at", desc=True)
                  .execute())
        return result.data or []
    
    def approve_action(self, action_id: str, user_id: str) -> dict:
        result = (self.client.table("action_log")
                  .update({"status": "approved", "approved_by": user_id, "approved_at": datetime.utcnow().isoformat()})
                  .eq("id", action_id)
                  .execute())
        return result.data[0] if result.data else None
    
    def reject_action(self, action_id: str, reason: str) -> dict:
        result = (self.client.table("action_log")
                  .update({"status": "rejected", "rejection_reason": reason})
                  .eq("id", action_id)
                  .execute())
        return result.data[0] if result.data else None
    
    # ── Memory ─────────────────────────────────────────────
    
    def save_memory(self, data: dict) -> dict:
        result = self.client.table("memory_store").insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_memories(self, user_id: str, memory_type: Optional[str] = None, limit: int = 20) -> list:
        query = self.client.table("memory_store").select("*").eq("user_id", user_id)
        if memory_type:
            query = query.eq("memory_type", memory_type)
        result = query.order("relevance_score", desc=True).limit(limit).execute()
        return result.data or []
    
    # ── Storage ────────────────────────────────────────────
    
    def upload_file(self, user_id: str, filename: str, file_bytes: bytes, content_type: str) -> str:
        """Upload file to Supabase Storage, return the path"""
        path = f"{user_id}/{uuid.uuid4()}/{filename}"
        self.client.storage.from_("case-documents").upload(
            path, file_bytes, {"content-type": content_type}
        )
        return path
    
    def get_file_url(self, path: str, expires_in: int = 3600) -> str:
        """Get signed URL for a file"""
        result = self.client.storage.from_("case-documents").create_signed_url(path, expires_in)
        return result.get("signedURL", "")
