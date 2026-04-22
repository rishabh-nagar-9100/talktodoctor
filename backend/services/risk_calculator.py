"""
Deterministic Risk Level Calculator — Phase 3.

Calculates a patient's risk level using keyword matching and
rule-based logic. This is COMPLETELY INDEPENDENT of the LLM
to ensure deterministic, auditable safety assessments.

The risk level is NOT a diagnosis — it's a triage priority hint
to help doctors optimize their queue.

Risk Levels:
  - HIGH:     Emergency-level keywords detected, immediate attention
  - MODERATE: Multiple symptoms, extended duration, or concerning patterns
  - LOW:      Minor symptoms, short duration, low concern

IMPORTANT: This calculator is conservative. It will over-flag rather
than under-flag to err on the side of patient safety.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  Critical Symptom Keywords
#  These ALWAYS trigger HIGH risk, regardless of other factors
# ══════════════════════════════════════════════

CRITICAL_SYMPTOMS = {
    # Cardiac
    "chest pain", "chest tightness", "heart palpitations", "palpitations",
    "irregular heartbeat", "heart attack",
    # Respiratory
    "shortness of breath", "difficulty breathing", "breathing difficulty",
    "can't breathe", "cannot breathe", "choking", "wheezing",
    # Neurological
    "loss of consciousness", "fainting", "fainted", "seizure", "seizures",
    "sudden numbness", "sudden weakness", "slurred speech", "confusion",
    "worst headache", "thunderclap headache", "stroke",
    # Trauma / Bleeding
    "severe bleeding", "heavy bleeding", "uncontrolled bleeding",
    "head injury", "head trauma", "broken bone", "fracture",
    # Mental Health
    "suicidal", "suicide", "self-harm", "self harm",
    "want to die", "kill myself",
    # Allergic
    "anaphylaxis", "severe allergic reaction", "throat swelling",
    "tongue swelling", "face swelling",
    # Other Critical
    "vomiting blood", "blood in stool", "high fever",
    "loss of vision", "sudden vision loss", "severe abdominal pain",
    "coughing blood",
}

# ══════════════════════════════════════════════
#  Concerning Symptom Keywords
#  These flag MODERATE risk when combined with other factors
# ══════════════════════════════════════════════

CONCERNING_SYMPTOMS = {
    "fever", "dizziness", "dizzy", "nausea", "vomiting",
    "diarrhea", "abdominal pain", "stomach pain", "stomach ache",
    "migraine", "severe headache", "blood pressure", "swelling",
    "rash", "numbness", "tingling", "weight loss", "fatigue",
    "insomnia", "anxiety", "depression", "muscle pain", "joint pain",
    "back pain", "neck pain", "cough", "sore throat",
    "ear pain", "eye pain", "blurry vision", "dehydration",
    "chills", "body ache", "weakness", "cramps",
}

# ══════════════════════════════════════════════
#  Duration Thresholds (days)
# ══════════════════════════════════════════════

LONG_DURATION_DAYS = 14    # 2+ weeks = adds risk
MEDIUM_DURATION_DAYS = 7   # 1+ week = moderate concern


def calculate_risk_level(summary: dict) -> dict:
    """
    Calculate a deterministic risk level from a patient summary.

    This function uses ONLY keyword matching and rule-based logic.
    No LLM, no ML model, no non-deterministic components.

    Args:
        summary: A PatientSummary dict with symptoms, severity, etc.

    Returns:
        dict with:
            - risk_level: "High", "Moderate", or "Low"
            - risk_score: 0-100 numeric score
            - risk_factors: list of reasons for the risk level
            - critical_flags: list of critical symptoms detected
    """
    risk_score = 0
    risk_factors = []
    critical_flags = []

    symptoms = summary.get("symptoms", [])
    severity = (summary.get("severity", "") or "").lower()
    additional_notes = (summary.get("additional_notes", "") or "").lower()
    chief_complaint = (summary.get("chief_complaint", "") or "").lower()

    # Combine all text for keyword matching
    all_text = " ".join([
        chief_complaint,
        additional_notes,
        " ".join(s.get("name", "").lower() for s in symptoms),
        " ".join(s.get("details", "").lower() for s in symptoms),
    ])

    # ── Rule 1: Critical Keyword Detection ──
    for keyword in CRITICAL_SYMPTOMS:
        if keyword in all_text:
            risk_score += 40
            critical_flags.append(keyword.title())
            risk_factors.append(f"Critical symptom detected: {keyword.title()}")

    # ── Rule 2: AI Severity Assessment ──
    if "severe" in severity:
        risk_score += 25
        risk_factors.append("AI assessed severity as Severe")
    elif "moderate" in severity:
        risk_score += 10
        risk_factors.append("AI assessed severity as Moderate")

    # ── Rule 3: Symptom Count ──
    symptom_count = len(symptoms)
    if symptom_count >= 4:
        risk_score += 15
        risk_factors.append(f"Multiple symptoms reported ({symptom_count})")
    elif symptom_count >= 2:
        risk_score += 5
        risk_factors.append(f"{symptom_count} symptoms reported")

    # ── Rule 4: Duration Analysis ──
    max_duration_days = _extract_max_duration_days(symptoms)
    if max_duration_days is not None:
        if max_duration_days >= LONG_DURATION_DAYS:
            risk_score += 15
            risk_factors.append(f"Extended duration ({max_duration_days}+ days)")
        elif max_duration_days >= MEDIUM_DURATION_DAYS:
            risk_score += 8
            risk_factors.append(f"Notable duration ({max_duration_days}+ days)")

    # ── Rule 5: Concerning Symptom Keywords ──
    concerning_found = []
    for keyword in CONCERNING_SYMPTOMS:
        if keyword in all_text:
            concerning_found.append(keyword.title())
    if len(concerning_found) >= 3:
        risk_score += 10
        risk_factors.append(f"Multiple concerning symptoms: {', '.join(concerning_found[:3])}")
    elif len(concerning_found) >= 1:
        risk_score += 3

    # ── Rule 6: Age-related risk ──
    age = summary.get("age", "Not specified")
    age_num = _parse_age(age)
    if age_num is not None:
        if age_num >= 65 or age_num <= 5:
            risk_score += 10
            risk_factors.append(f"Age-related risk factor (age: {age_num})")
        elif age_num <= 12:
            risk_score += 5
            risk_factors.append(f"Pediatric patient (age: {age_num})")

    # ── Cap score at 100 ──
    risk_score = min(risk_score, 100)

    # ── Determine risk level ──
    if risk_score >= 40 or len(critical_flags) > 0:
        risk_level = "High"
    elif risk_score >= 20:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # If no risk factors found, add a default
    if not risk_factors:
        risk_factors.append("No significant risk factors detected")

    result = {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "critical_flags": critical_flags,
    }

    logger.info(
        f"Risk assessment: {risk_level} (score={risk_score}, "
        f"flags={len(critical_flags)}, factors={len(risk_factors)})"
    )

    return result


def is_critical_symptom(symptom_name: str) -> bool:
    """
    Check if a symptom name matches any critical keyword.
    Used by the frontend to highlight individual symptoms.

    Args:
        symptom_name: The symptom name to check.

    Returns:
        True if the symptom is critical.
    """
    name_lower = symptom_name.lower().strip()
    for keyword in CRITICAL_SYMPTOMS:
        if keyword in name_lower or name_lower in keyword:
            return True
    return False


def get_critical_keywords() -> list[str]:
    """Return the list of critical symptom keywords for frontend use."""
    return sorted(CRITICAL_SYMPTOMS)


def _extract_max_duration_days(symptoms: list[dict]) -> Optional[int]:
    """
    Extract the maximum reported symptom duration in days.
    Parses natural language duration strings like '3 days', '2 weeks', '1 month'.
    """
    max_days = None

    for symptom in symptoms:
        duration = (symptom.get("duration", "") or "").lower()
        if not duration or duration == "not specified":
            continue

        days = _parse_duration_to_days(duration)
        if days is not None:
            if max_days is None or days > max_days:
                max_days = days

    return max_days


def _parse_duration_to_days(duration_str: str) -> Optional[int]:
    """
    Parse a duration string to approximate number of days.
    Examples: '3 days' → 3, '2 weeks' → 14, '1 month' → 30
    """
    import re

    duration_str = duration_str.lower().strip()

    # Try to find a number + unit pattern
    match = re.search(r'(\d+)\s*(day|week|month|year|hour)', duration_str)
    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if 'hour' in unit:
            return max(1, num // 24)
        elif 'day' in unit:
            return num
        elif 'week' in unit:
            return num * 7
        elif 'month' in unit:
            return num * 30
        elif 'year' in unit:
            return num * 365

    # Handle "a few days" type patterns
    if 'few days' in duration_str:
        return 3
    if 'few weeks' in duration_str:
        return 21
    if 'long time' in duration_str:
        return 30

    return None


def _parse_age(age_str: str) -> Optional[int]:
    """
    Parse an age string to an integer.
    Examples: '32', '32 years', 'sixty' → numeric value
    """
    import re

    if not age_str or age_str.lower() in ('not specified', 'unknown', 'n/a'):
        return None

    match = re.search(r'(\d+)', age_str)
    if match:
        return int(match.group(1))

    return None
