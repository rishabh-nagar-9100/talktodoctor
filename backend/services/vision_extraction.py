"""
Medical Report Vision Analysis Service — Phase 4.

Uses OpenAI GPT-4o with Vision capabilities to extract structured
data from uploaded medical reports (X-rays, lab results).
"""

import base64
import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

VISION_PROMPT = """
You are an expert medical AI assistant.
Your task is to analyze the provided medical report image (e.g., X-ray, lab results, MRI report) and extract the key information.

You must output a JSON object with the following structure:
{
  "report_type": "The type of report (e.g., 'Chest X-ray', 'Blood Test', 'Unknown')",
  "findings": [
    "List of key objective findings extracted from the text or clearly visible in the report."
  ],
  "impressions": "The overall clinical impression or conclusion stated in the report.",
  "flagged_abnormalities": [
    "List of explicitly flagged abnormalities (e.g., High cholesterol, Fracture seen)."
  ]
}

DO NOT DIAGNOSE based on visual artifacts alone unless it is explicitly written in the report text. If the image is illegible or not a medical report, return report_type as "Invalid/Unreadable" and empty lists.
"""

async def analyze_medical_report(image_bytes: bytes, mime_type: str) -> dict:
    """
    Send an image to GPT-4o vision for extraction.
    
    Args:
        image_bytes: The raw image bytes.
        mime_type: The image mime type (e.g., 'image/jpeg', 'application/pdf').
        
    Returns:
        A dict matching the MedicalReport schema structure.
    """
    try:
        # We need base64 encoded image for OpenAI vision
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # If it's a PDF, OpenAI vision doesn't natively accept PDF yet via this exact image_url format
        # but for Phase 4 MVP we will assume it's an image (png/jpeg)
        if "pdf" in mime_type.lower():
            logger.warning("PDF uploaded. We will attempt vision parsing but image conversion may be needed.")

        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that strictly outputs JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VISION_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.1
        )

        raw = response.choices[0].message.content
        logger.debug(f"Vision AI raw response: {raw}")
        parsed = json.loads(raw)
        
        return {
            "report_type": parsed.get("report_type", "Unknown Report"),
            "findings": parsed.get("findings", []),
            "impressions": parsed.get("impressions", "No impression found."),
            "flagged_abnormalities": parsed.get("flagged_abnormalities", [])
        }

    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        return {
            "report_type": "Error processing report",
            "findings": [f"Error: {str(e)}"],
            "impressions": "",
            "flagged_abnormalities": []
        }
