"""
Medical Report Analysis Router — Phase 4.

Provides an endpoint to upload and analyze medical reports
(X-rays, lab results) using AI Vision.
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.models.schemas import MedicalReport
from backend.services.vision_extraction import analyze_medical_report
from backend.routers.patient import reports_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/reports/analyze",
    response_model=MedicalReport,
    summary="Analyze a medical report image",
    description="Extracts findings and impressions from an uploaded medical report using AI Vision.",
)
async def process_report(
    file: UploadFile = File(..., description="Image of the medical report (jpeg, png)"),
    patient_id: str = Form(..., description="ID of the patient this report belongs to")
):
    """
    1. Read the uploaded file.
    2. Send to GPT-4o Vision for extraction.
    3. Save to reports database.
    """
    logger.info(f"Received report upload: {file.filename} for patient {patient_id}")
    
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    mime_type = file.content_type or "image/jpeg"
    
    # Send to AI
    extracted_data = await analyze_medical_report(file_bytes, mime_type)
    
    # Build report object
    report = MedicalReport(
        id=f"rep-{uuid.uuid4().hex[:6]}",
        patient_id=patient_id,
        report_type=extracted_data.get("report_type", "Unknown"),
        findings=extracted_data.get("findings", []),
        impressions=extracted_data.get("impressions", ""),
        flagged_abnormalities=extracted_data.get("flagged_abnormalities", [])
    )
    
    # Save to mock DB
    reports_db.append(report.model_dump())
    
    logger.info(f"Report analyzed and saved with ID {report.id}")
    return report
