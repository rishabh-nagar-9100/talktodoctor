"""
Patient management and history tracking — Phase 4.

Provides an in-memory patient database to link intakes and
medical reports to specific patients, enabling longitudinal
history tracking.
"""

import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.schemas import Patient
from backend.db.supabase import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ──────────────────────────────────────────────
# Simulated In-Memory Database
# ──────────────────────────────────────────────
patients_db: List[Patient] = [
    # Seed with one test patient
    Patient(
        id="pt-101",
        name="John Doe",
        age=45,
        gender="Male",
    )
]

# Separate list for medical reports to simulate table
reports_db: list[dict] = []


class CreatePatientRequest(BaseModel):
    name: str
    age: int
    gender: str


@router.post(
    "/patients",
    response_model=Patient,
    summary="Create a new patient",
)
async def create_patient(req: CreatePatientRequest):
    """Register a new patient."""
    new_patient = Patient(
        id=f"pt-{uuid.uuid4().hex[:6]}",
        name=req.name,
        age=req.age,
        gender=req.gender,
    )
    patients_db.append(new_patient)
    logger.info(f"Created patient {new_patient.id}")
    return new_patient


@router.get(
    "/patients",
    response_model=List[Patient],
    summary="List all patients",
)
async def get_patients():
    """Get all registered patients."""
    return patients_db


@router.get(
    "/patients/{patient_id}",
    response_model=Patient,
    summary="Get patient details",
)
async def get_patient(patient_id: str):
    """Get a specific patient by ID."""
    db = get_db()
    res = db.table("patients").select("*").eq("id", patient_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Patient not found.")
    
    p = res.data[0]
    return Patient(
        id=p["id"],
        name=p.get("phone_number", "Unknown"), # We only store phone_number in MVP right now
        age=0,
        gender="Unknown"
    )


@router.get(
    "/patients/{patient_id}/history",
    summary="Get patient longitudinal history",
    description="Returns all intakes and reports associated with this patient.",
)
async def get_patient_history(patient_id: str):
    """Retrieve all intakes and medical reports for a given patient."""
    db = get_db()
    res_p = db.table("patients").select("*").eq("id", patient_id).execute()
    if not res_p.data:
        raise HTTPException(status_code=404, detail="Patient not found.")
    patient = res_p.data[0]
    
    res = db.table("medical_summaries").select("*, intake_sessions(completed_at)").eq("patient_id", patient_id).execute()
    
    patient_intakes = []
    for s in res.data:
        patient_intakes.append({
            "id": s["session_id"],
            "timestamp": s.get("intake_sessions", {}).get("completed_at"),
            "data": {
                "summary": s
            }
        })
            
    # Find reports
    patient_reports = []
            
    # Sort by timestamp (newest first)
    patient_intakes.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return {
        "patient": patient,
        "intakes": patient_intakes,
        "reports": patient_reports
    }
