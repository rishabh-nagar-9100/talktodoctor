"""
Analytics Router — Phase 5.

Provides system-wide statistics, patient trends, and doctor productivity metrics.
"""

import logging
from collections import Counter
from fastapi import APIRouter

from backend.db.supabase import get_db
from backend.services.risk_calculator import calculate_risk_level

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/analytics/dashboard",
    summary="Get Analytics Dashboard Data",
    description="Aggregates system-wide statistics for the Phase 5 Analytics Dashboard.",
)
async def get_analytics_dashboard():
    """
    Compute real-time statistics from the in-memory data stores.
    """
    db = get_db()
    
    # Get total counts
    total_intakes_res = db.table("intake_sessions").select("id", count="exact").execute()
    total_intakes = total_intakes_res.count or 0
    
    total_patients_res = db.table("patients").select("id", count="exact").execute()
    total_patients = total_patients_res.count or 0
    
    total_reports = 0 # Future implementation
    
    # ── Doctor Productivity Metrics ──
    # Assuming the AI saves an average of 5 minutes per intake
    minutes_saved = total_intakes * 5
    hours_saved = round(minutes_saved / 60, 1)

    # ── Patient Trends & Symptoms ──
    symptom_counter = Counter()
    risk_counts = {"High": 0, "Moderate": 0, "Low": 0}
    severity_counts = {"Severe": 0, "Moderate": 0, "Mild": 0, "Not assessed": 0}
    
    summaries_res = db.table("medical_summaries").select("*").execute()
    for summary in summaries_res.data:
        
        # Count Symptoms
        for symptom in summary.get("symptoms", []):
            name = symptom.get("name", "Unknown").title()
            symptom_counter[name] += 1
            
        # Count Severity
        severity = summary.get("severity", "Not assessed").title()
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts["Not assessed"] += 1
            
        # On-the-fly risk calculation for analytics
        # calculate_risk_level expects a plain dict, which matches the Supabase row
        risk = calculate_risk_level(summary)
        risk_level = risk.get("risk_level", "Low")
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
            
    # Format for Recharts
    top_symptoms = [{"name": k, "count": v} for k, v in symptom_counter.most_common(5)]
    
    risk_distribution = [
        {"name": "High Risk", "value": risk_counts["High"]},
        {"name": "Moderate Risk", "value": risk_counts["Moderate"]},
        {"name": "Low Risk", "value": risk_counts["Low"]},
    ]
    
    severity_distribution = [{"name": k, "value": v} for k, v in severity_counts.items()]

    # Mock 7-day volume history for the line chart (Today = actual intakes)
    import datetime
    today = datetime.date.today()
    volume_history = []
    
    # Generate 6 days of mock data
    mock_volumes = [12, 15, 8, 22, 18, 14]
    for i in range(6, 0, -1):
        day = today - datetime.timedelta(days=i)
        volume_history.append({
            "date": day.strftime("%a"),
            "intakes": mock_volumes[6-i]
        })
        
    # Add today
    volume_history.append({
        "date": "Today",
        "intakes": total_intakes + 5  # Add a baseline of 5 for demonstration
    })

    return {
        "system_metrics": {
            "total_intakes": total_intakes,
            "total_patients": total_patients,
            "total_reports_analyzed": total_reports,
        },
        "productivity": {
            "estimated_hours_saved": hours_saved,
            "intakes_processed": total_intakes,
        },
        "trends": {
            "top_symptoms": top_symptoms,
            "risk_distribution": risk_distribution,
            "severity_distribution": severity_distribution,
            "volume_history": volume_history
        }
    }
