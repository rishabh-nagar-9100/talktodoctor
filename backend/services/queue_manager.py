"""
Queue Manager Service (Phase 7)
Handles token generation, queue sorting, and wait time calculation.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from backend.models.schemas import QueueItem, QueueStatus

from backend.db.supabase import get_db

logger = logging.getLogger(__name__)

AVERAGE_CONSULT_TIME_MINS = 10

def generate_token(urgency: str, db) -> str:
    """Generate a simple clinic token (e.g., G-01, U-02)."""
    prefix = "U" if urgency.lower() in ["urgent", "emergency"] else "G"
    
    # Count how many of this prefix exist today
    # For MVP we count total historical for simplicity, or we can just count all
    try:
        res = db.table("queue_items").select("id", count="exact").ilike("token_number", f"{prefix}-%").execute()
        count = res.count or 0
    except Exception:
        count = 0
        
    return f"{prefix}-{count + 1:02d}"

def add_to_queue(intake_id: str, urgency_level: str, phone_number: Optional[str] = None) -> QueueItem:
    """Add a patient to the queue and calculate estimated wait time."""
    db = get_db()
    
    # 1. Ensure Patient Exists
    patient_id = None
    if phone_number:
        # Check if patient exists
        res = db.table("patients").select("id").eq("phone_number", phone_number).execute()
        if res.data and len(res.data) > 0:
            patient_id = res.data[0]["id"]
        else:
            # Create patient
            new_patient = db.table("patients").insert({"phone_number": phone_number}).execute()
            if new_patient.data:
                patient_id = new_patient.data[0]["id"]
                
    # 2. Update Session & Summary with patient_id
    if patient_id:
        db.table("intake_sessions").update({"patient_id": patient_id}).eq("id", intake_id).execute()
        db.table("medical_summaries").update({"patient_id": patient_id}).eq("session_id", intake_id).execute()

    token = generate_token(urgency_level, db)
    
    # Calculate wait time
    res = db.table("queue_items").select("id", count="exact").eq("status", "waiting").execute()
    waiting_count = res.count or 0
    wait_mins = waiting_count * AVERAGE_CONSULT_TIME_MINS
    
    expected_time = (datetime.now(timezone.utc) + timedelta(minutes=wait_mins)).isoformat()

    queue_data = {
        "session_id": intake_id,
        "patient_id": patient_id,
        "token_number": token,
        "status": "waiting",
        "urgency_level": "urgent" if urgency_level.lower() in ["urgent", "emergency"] else "general",
        "expected_time": expected_time
    }
    
    # Insert queue item
    inserted = db.table("queue_items").insert(queue_data).execute()
    new_item = inserted.data[0]

    queue_item = QueueItem(
        id=new_item["id"],
        intake_id=intake_id,
        token_number=token,
        status=QueueStatus.WAITING,
        urgency_level=queue_data["urgency_level"],
        expected_time=expected_time,
        phone_number=phone_number
    )
    
    logger.info(f"Added Intake {intake_id} to DB queue with token {token}. Wait time: ~{wait_mins} mins")
    return queue_item

def get_live_queue() -> List[QueueItem]:
    """Return the active queue sorted by urgency then time from Supabase."""
    db = get_db()
    
    # Fetch all waiting and in_consultation items
    # Also join patient to get phone number
    res = db.table("queue_items").select("*, patients(phone_number)").in_("status", ["waiting", "in_consultation"]).execute()
    items = res.data
    
    # Convert to QueueItem objects
    queue_objects = []
    for q in items:
        phone = q.get("patients", {}).get("phone_number") if q.get("patients") else None
        queue_objects.append(QueueItem(
            id=q["id"],
            intake_id=q["session_id"],
            token_number=q["token_number"],
            status=QueueStatus(q["status"]),
            urgency_level=q.get("urgency_level", "general"),
            expected_time=q.get("expected_time"),
            joined_at=q.get("joined_at"),
            phone_number=phone
        ))
        
    # Urgent first, then chronological
    waiting = [q for q in queue_objects if q.status == QueueStatus.WAITING]
    urgent = sorted([q for q in waiting if q.urgency_level == "urgent"], key=lambda x: x.joined_at)
    general = sorted([q for q in waiting if q.urgency_level == "general"], key=lambda x: x.joined_at)
    
    in_consult = [q for q in queue_objects if q.status == QueueStatus.IN_CONSULTATION]
    
    return in_consult + urgent + general

def update_queue_status(queue_id: str, new_status: QueueStatus) -> Optional[QueueItem]:
    """Update a patient's status in the queue."""
    db = get_db()
    
    update_data = {"status": new_status.value}
    if new_status in [QueueStatus.COMPLETED, QueueStatus.SKIPPED]:
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        
    res = db.table("queue_items").update(update_data).eq("id", queue_id).execute()
    if not res.data:
        return None
        
    # Get phone number if available
    q = res.data[0]
    patient_res = db.table("patients").select("phone_number").eq("id", q["patient_id"]).execute() if q.get("patient_id") else None
    phone = patient_res.data[0]["phone_number"] if patient_res and patient_res.data else None
    
    logger.info(f"Updated token {q['token_number']} status to {new_status}")
    
    return QueueItem(
        id=q["id"],
        intake_id=q["session_id"],
        token_number=q["token_number"],
        status=QueueStatus(q["status"]),
        urgency_level=q.get("urgency_level", "general"),
        expected_time=q.get("expected_time"),
        joined_at=q.get("joined_at"),
        phone_number=phone
    )
