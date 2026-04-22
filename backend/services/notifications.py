"""
Notification Service (Phase 7)
Mock implementation of SMS and Email notifications using Twilio/SendGrid patterns.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def send_sms(phone_number: str, message: str) -> bool:
    """
    Mock sending an SMS.
    In production, this would use the Twilio SDK:
    client.messages.create(body=message, from_=TWILIO_PHONE, to=phone_number)
    """
    if not phone_number:
        logger.warning("Attempted to send SMS without a phone number.")
        return False
        
    logger.info("=" * 50)
    logger.info(f"📱 MOCK SMS TO: {phone_number}")
    logger.info(f"✉️  MESSAGE: {message}")
    logger.info("=" * 50)
    return True

def notify_patient_joined_queue(phone_number: str, token: str, wait_mins: int):
    """Send SMS when patient successfully completes intake and gets a token."""
    msg = (
        f"TalkToDoctor: Aapka token {token} confirm ho gaya hai. XYZ Clinic.\n"
        f"Estimated wait: ~{wait_mins} mins.\n"
        f"Live status check karein: http://localhost:5173/queue/live"
    )
    send_sms(phone_number, msg)

def notify_patient_turn_approaching(phone_number: str, token: str, currently_serving: str):
    """Send SMS when patient is next or almost next."""
    msg = (
        f"TalkToDoctor: Please be ready! Aapka turn jaldi aane wala hai.\n"
        f"Your Token: {token}\n"
        f"Currently serving: {currently_serving}"
    )
    send_sms(phone_number, msg)

def notify_patient_ready(phone_number: str, token: str):
    """Send SMS when the doctor calls the patient."""
    msg = (
        f"TalkToDoctor: {token}, Doctor is ready.\n"
        f"Please proceed to Cabin 1 immediately."
    )
    send_sms(phone_number, msg)
