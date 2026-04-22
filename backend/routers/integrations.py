"""
Hospital Integrations Router — Phase 5.

Provides mock webhooks/endpoints to simulate exporting structured data
to external EHR (Electronic Health Record) systems via FHIR/HL7 formats.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from backend.db.supabase import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/integrations/ehr/export/{intake_id}",
    summary="Mock Export to EHR",
    description="Simulates pushing structured intake data to a hospital EHR system using a mock FHIR payload.",
)
async def export_to_ehr(intake_id: str):
    """
    1. Find the intake record.
    2. Format it into a simulated FHIR-like payload.
    3. Return a simulated success response.
    """
    db = get_db()
    res = db.table("medical_summaries").select("*, intake_sessions(completed_at)").eq("session_id", intake_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Intake #{intake_id} not found.")

    summary = res.data[0]
    patient_id = summary.get("patient_id", "Unknown")
    timestamp = summary.get("intake_sessions", {}).get("completed_at", datetime.utcnow().isoformat())

    # ── Simulated FHIR-like Payload ──
    fhir_payload = {
        "resourceType": "Encounter",
        "status": "arrived",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "EMER",
            "display": "Emergency"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "reasonCode": [
            {
                "text": summary.get("chief_complaint", "Unknown")
            }
        ],
        "period": {
            "start": timestamp
        },
        "contained": [
            {
                "resourceType": "Condition",
                "clinicalStatus": {
                    "coding": [{"code": "active"}]
                },
                "code": {"text": s.get("name")}
            } for s in summary.get("symptoms", [])
        ],
        "note": [
            {
                "text": summary.get("additional_notes", "")
            }
        ]
    }

    logger.info(f"Simulated EHR export for Intake #{intake_id} (Patient: {patient_id})")

    return {
        "status": "success",
        "message": "Successfully exported to EHR",
        "simulated_destination": "Epic Systems (Mock Endpoint)",
        "payload_size_bytes": len(str(fhir_payload)),
        "simulated_payload": fhir_payload
    }
