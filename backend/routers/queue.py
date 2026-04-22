"""
Queue Management Router (Phase 7)
Endpoints for joining the queue, viewing the live queue, and doctor queue controls.
"""
import logging
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional

from backend.models.schemas import QueueItem, QueueStatus
from backend.services.queue_manager import (
    add_to_queue, get_live_queue, update_queue_status, AVERAGE_CONSULT_TIME_MINS
)
from backend.services.notifications import (
    notify_patient_joined_queue, notify_patient_ready, notify_patient_turn_approaching
)
from backend.db.supabase import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queue", tags=["Queue"])

@router.post("/join")
async def join_queue(
    intake_id: str = Body(..., embed=True),
    phone_number: str = Body(..., embed=True)
):
    """
    Patient joins the queue after completing their AI intake.
    Generates a token and sends a confirmation SMS.
    """
    # Find the summary record to determine urgency
    db = get_db()
    res = db.table("medical_summaries").select("urgency_level").eq("session_id", intake_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Medical summary not found for this session.")
        
    urgency = res.data[0].get("urgency_level", "general")
    
    # Add to queue
    queue_item = add_to_queue(intake_id, urgency, phone_number)
    
    # Calculate wait time for the SMS
    res = db.table("queue_items").select("id", count="exact").eq("status", "waiting").execute()
    waiting_count = res.count or 0
    wait_mins = waiting_count * AVERAGE_CONSULT_TIME_MINS
    
    # Send mock SMS
    notify_patient_joined_queue(phone_number, queue_item.token_number, max(wait_mins, 0))
    
    return {
        "status": "success",
        "token": queue_item.token_number,
        "queue_id": queue_item.id,
        "expected_wait_mins": wait_mins
    }

@router.get("/live")
async def get_queue() -> List[QueueItem]:
    """Get the live queue (sorted for the doctor dashboard)."""
    return get_live_queue()

@router.post("/{queue_id}/call")
async def call_patient(queue_id: str):
    """Doctor clicks 'Call Next' - updates status to IN_CONSULTATION and sends SMS."""
    item = update_queue_status(queue_id, QueueStatus.IN_CONSULTATION)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found.")
        
    if item.phone_number:
        notify_patient_ready(item.phone_number, item.token_number)
        
    # Check if there is a "next" patient to notify them to get ready
    live = get_live_queue()
    waiting = [q for q in live if q.status == QueueStatus.WAITING]
    if len(waiting) > 0 and waiting[0].phone_number:
        notify_patient_turn_approaching(
            waiting[0].phone_number, 
            waiting[0].token_number, 
            item.token_number
        )
        
    return item

@router.post("/{queue_id}/complete")
async def complete_patient(queue_id: str):
    """Doctor clicks 'Mark Completed'."""
    item = update_queue_status(queue_id, QueueStatus.COMPLETED)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found.")
    return item

@router.post("/{queue_id}/skip")
async def skip_patient(queue_id: str):
    """Doctor clicks 'Skip / No-Show'."""
    item = update_queue_status(queue_id, QueueStatus.SKIPPED)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found.")
    return item
