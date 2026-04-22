/**
 * DoctorDashboard Component — Phase 3: Doctor Efficiency System
 *
 * Advanced clinical dashboard with:
 * - Quick Patient Summary sidebar (10-second scan)
 * - Risk level meter with deterministic scoring
 * - Critical symptom flagging (red-highlighted)
 * - AI-suggested follow-up questions with categories
 * - Collapsible transcript and conversation history
 *
 * The AI NEVER diagnoses. This is a decision-support tool only.
 * The treating physician is the FINAL authority.
 */

import { useState, useEffect, useCallback } from 'react';
import { getAllIntakes, analyzeIntake, getRiskKeywords, analyzeReport, exportToEHR } from '../services/api';
import './DoctorDashboard.css';

// Critical keywords for frontend-side symptom highlighting
const CRITICAL_KEYWORDS_LOCAL = [
  'chest pain', 'shortness of breath', 'difficulty breathing',
  'loss of consciousness', 'severe bleeding', 'seizure', 'stroke',
  'suicidal', 'heart attack', 'anaphylaxis', 'choking', 'fainting',
  'vomiting blood', 'coughing blood',
];

export default function DoctorDashboard({ latestIntake }) {
  // ── State ──
  const [intakes, setIntakes] = useState([]);
  const [liveQueue, setLiveQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSections, setExpandedSections] = useState({});
  const [selectedIntake, setSelectedIntake] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [criticalKeywords, setCriticalKeywords] = useState(CRITICAL_KEYWORDS_LOCAL);

  // ── Phase 4: Report Analysis State ──
  const [reportUploading, setReportUploading] = useState(false);
  const [reportResult, setReportResult] = useState(null);

  // ── Phase 5: Export to EHR State ──
  const [exportingEHR, setExportingEHR] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // Lazy import queue functions
      const { getLiveQueue } = await import('../services/api');
      const [allIntakes, queueData] = await Promise.all([
        getAllIntakes(),
        getLiveQueue().catch(() => [])
      ]);
      
      setIntakes(allIntakes || []);
      setLiveQueue(queueData || []);
      
      // Auto-select the first item in the queue if none selected
      if (queueData?.length > 0 && !selectedIntake) {
        const firstIntake = allIntakes.find(i => i.id === queueData[0].intake_id);
        if (firstIntake) setSelectedIntake(firstIntake);
      } else if (allIntakes?.length > 0 && !selectedIntake) {
        setSelectedIntake(allIntakes[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Fetch critical keywords from backend ──
  useEffect(() => {
    getRiskKeywords()
      .then((data) => {
        if (data?.critical_keywords) {
          setCriticalKeywords(data.critical_keywords);
        }
      })
      .catch(() => { /* Use local fallback */ });
  }, []);

  // ── Fetch on mount and when new intake arrives ──
  useEffect(() => {
    fetchDashboardData();
    // Refresh queue every 10 seconds
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, [fetchDashboardData, latestIntake]);

  // ── Run doctor analysis when an intake is selected ──
  const runAnalysis = useCallback(async (intake) => {
    if (!intake) return;
    setAnalysisLoading(true);
    setAnalysis(null);
    try {
      const result = await analyzeIntake(intake.id);
      setAnalysis(result.analysis);
    } catch (err) {
      console.error('Analysis error:', err);
      // Fallback — show basic info without analysis
      setAnalysis(null);
    } finally {
      setAnalysisLoading(false);
    }
  }, []);

  // ── Select an intake (from sidebar list) ──
  const handleSelectIntake = (intake) => {
    setSelectedIntake(intake);
    setAnalysis(null);
  };

  // ── Toggle collapsible sections ──
  const toggleSection = (key) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // ── Check if a symptom is critical ──
  const isCriticalSymptom = (symptomName) => {
    const name = (symptomName || '').toLowerCase();
    return criticalKeywords.some((kw) => name.includes(kw) || kw.includes(name));
  };

  // ── Format timestamp ──
  const formatTimestamp = (iso) => {
    try {
      return new Date(iso).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return iso;
    }
  };

  // ── Severity helpers ──
  const getSeverityClass = (s) => {
    const val = (s || '').toLowerCase();
    if (val.includes('severe')) return 'severity-severe';
    if (val.includes('moderate')) return 'severity-moderate';
    return 'severity-mild';
  };

  const getSeverityIcon = (s) => {
    const val = (s || '').toLowerCase();
    if (val.includes('severe')) return '🔴';
    if (val.includes('moderate')) return '🟡';
    return '🟢';
  };

  // ── Risk level helpers ──
  const getRiskClass = (level) => {
    const val = (level || '').toLowerCase();
    if (val.includes('high')) return 'risk-high';
    if (val.includes('moderate')) return 'risk-moderate';
    return 'risk-low';
  };

  const getRiskIcon = (level) => {
    const val = (level || '').toLowerCase();
    if (val.includes('high')) return '🚨';
    if (val.includes('moderate')) return '⚠️';
    return '✅';
  };

  // ── Priority helpers for follow-up questions ──
  const getPriorityClass = (priority) => {
    const val = (priority || '').toLowerCase();
    if (val === 'high') return 'priority-high';
    if (val === 'medium') return 'priority-medium';
    return 'priority-low';
  };

  // ── Phase 4: Handle Report Upload ──
  const handleUploadReport = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setReportUploading(true);
    setReportResult(null);
    try {
      // Mock patient ID for MVP Phase 4
      const res = await analyzeReport(file, "pt-101");
      setReportResult(res);
    } catch (err) {
      alert("Failed to analyze report: " + err.message);
    } finally {
      setReportUploading(false);
      // Reset input
      e.target.value = '';
    }
  };

  // ── Phase 5: Export to EHR ──
  const handleExportEHR = async (intakeId) => {
    setExportingEHR(true);
    try {
      const res = await exportToEHR(intakeId);
      alert(`Success: ${res.message}\nSimulated Destination: ${res.simulated_destination}\nPayload size: ${res.payload_size_bytes} bytes`);
    } catch (err) {
      alert("Export failed: " + err.message);
    } finally {
      setExportingEHR(false);
    }
  };

  const handleCallPatient = async (queueId) => {
    try {
      const { callPatient } = await import('../services/api');
      await callPatient(queueId);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCompletePatient = async (queueId) => {
    try {
      const { completePatient } = await import('../services/api');
      await completePatient(queueId);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSkipPatient = async (queueId) => {
    try {
      const { skipPatient } = await import('../services/api');
      await skipPatient(queueId);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  const selected = selectedIntake;
  const summary = selected?.data?.summary || {};
  const transcript = selected?.data?.transcript || '';
  const conversationHistory = selected?.data?.conversation_history || [];

  const activeQueueItem = selectedIntake 
    ? liveQueue.find(q => q.intake_id === selectedIntake.id)
    : null;

  const currentServing = liveQueue.find(q => q.status === 'in_consultation');

  return (
    <section className="dashboard" id="doctor-dashboard">

      {/* ── NOW SERVING BANNER ── */}
      {currentServing && (
        <div style={{
          background: 'linear-gradient(90deg, var(--accent-green), hsl(155, 60%, 35%))',
          color: 'white',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 4px 12px rgba(74, 222, 128, 0.2)'
        }}>
          <h2 style={{margin: 0, fontSize: '1.5rem'}}>🗣️ NOW SERVING: {currentServing.token_number}</h2>
          <button className="btn" style={{background: 'white', color: 'black'}} onClick={() => handleCompletePatient(currentServing.id)}>
            Mark Completed
          </button>
        </div>
      )}

      {/* ── Disclaimer Banner ── */}
      <div className="disclaimer-banner" role="alert">
        <span className="disclaimer-icon">⚠️</span>
        <span>
          <strong>AI-Generated Summary</strong> — This information was extracted
          by an AI assistant and is NOT a diagnosis. Always verify all details
          directly with the patient. The treating physician is the final authority.
        </span>
      </div>

      <div className="dashboard-layout">

        {/* ═══════════════════════════════════════ */}
        {/*  LEFT: Intake List Sidebar              */}
        {/* ═══════════════════════════════════════ */}
        <aside className="intake-sidebar">
          <div className="sidebar-header">
            <h3>🎟️ Live Queue ({liveQueue.filter(q => q.status === 'waiting').length} Waiting)</h3>
            <button
              id="refresh-dashboard-btn"
              className="btn-icon"
              onClick={fetchDashboardData}
              disabled={loading}
              title="Refresh Queue"
            >
              {loading ? '⏳' : '🔄'}
            </button>
          </div>

          {error && (
            <div className="sidebar-error">❌ {error}</div>
          )}

          {liveQueue.length === 0 && !loading && (
            <div className="sidebar-empty">
              <span>🩺</span>
              <p>Queue is empty</p>
            </div>
          )}

          <div className="intake-list">
            {liveQueue.filter(q => q.status === 'waiting').map((qItem) => {
              const intake = intakes.find(i => i.id === qItem.intake_id);
              if (!intake) return null;
              
              const s = intake.data?.summary || {};
              const isActive = selected?.id === intake.id;

              return (
                <button
                  key={qItem.id}
                  className={`intake-list-item ${isActive ? 'active' : ''} ${qItem.urgency_level === 'urgent' ? 'has-critical' : ''}`}
                  onClick={() => handleSelectIntake(intake)}
                >
                  <div className="item-top">
                    <span className="item-id">
                      <strong style={{fontSize: '1.1rem', color: qItem.urgency_level === 'urgent' ? 'var(--accent-red)' : 'var(--accent-blue)'}}>
                        {qItem.token_number}
                      </strong>
                    </span>
                    <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
                      ~{new Date(qItem.expected_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>
                  <div className="item-complaint">{s.chief_complaint || 'No complaint'}</div>
                  <div className="item-meta">
                    <span className={`mini-severity ${getSeverityClass(s.severity)}`}>
                      {getSeverityIcon(s.severity)} {s.severity || '—'}
                    </span>
                    <span className="item-time">
                      {s.age || '?'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* ═══════════════════════════════════════ */}
        {/*  CENTER: Main Content                   */}
        {/* ═══════════════════════════════════════ */}
        <main className="dashboard-main">
          {!selected ? (
            <div className="no-selection glass-card">
              <div className="empty-icon">🩺</div>
              <h3>Select a Patient Intake</h3>
              <p>Choose an intake from the sidebar to view the full summary with risk analysis.</p>
            </div>
          ) : (
            <>
              {/* ── Header ── */}
              <div className="main-header">
                <div>
                  <h2 className="patient-title">Patient Intake #{selected.id}</h2>
                  <span className="patient-time">🕐 {formatTimestamp(selected.timestamp)}</span>
                </div>
              </div>

              {/* ═══════════════════════════════ */}
              {/*  1. Quick Actions & Queue Controls */}
              {/* ═══════════════════════════════ */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                {activeQueueItem && activeQueueItem.status === 'waiting' && (
                  <>
                    <button className="btn btn-primary" onClick={() => handleCallPatient(activeQueueItem.id)}>
                      📢 Call Patient
                    </button>
                    <button className="btn btn-danger" onClick={() => handleSkipPatient(activeQueueItem.id)}>
                      ⏭️ Skip / No Show
                    </button>
                  </>
                )}
                {activeQueueItem && activeQueueItem.status === 'in_consultation' && (
                  <button className="btn" style={{background: 'var(--accent-green)', color: 'black'}} onClick={() => handleCompletePatient(activeQueueItem.id)}>
                    ✅ Mark Completed
                  </button>
                )}
                <div style={{flex: 1}}></div>
                <button
                  className="btn btn-secondary"
                  onClick={() => runAnalysis(selected)}
                  disabled={analysisLoading}
                >
                  {analysisLoading ? '⏳ Analyzing...' : '🧠 AI Risk Analysis'}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleExportEHR(selected.id)}
                  disabled={exportingEHR}
                >
                  {exportingEHR ? '⏳ Exporting...' : '📤 Export to EHR'}
                </button>
              </div>

              {/* ═══════════════════════════════ */}
              {/*  2. Critical Alerts           */}
              {/* ═══════════════════════════════ */}
              {(analysis?.risk_assessment?.urgency_level === 'Emergency' || 
                analysis?.risk_assessment?.urgency_level === 'Urgent' ||
                analysis?.risk_assessment?.critical_flags?.length > 0) && (
                <div className="alert-banner" style={{ background: 'hsla(0, 80%, 50%, 0.15)', borderLeft: '4px solid var(--critical-red)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                  <h3 style={{ color: 'var(--critical-red)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', margin: 0, marginBottom: '0.5rem' }}>
                    🚨 CRITICAL ALERT
                  </h3>
                  <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                    {analysis?.risk_assessment?.critical_flags?.map((flag, idx) => (
                      <li key={idx}><strong>{flag}</strong></li>
                    ))}
                    <li>Urgency Level: <strong>{analysis?.risk_assessment?.urgency_level}</strong></li>
                  </ul>
                </div>
              )}

              {/* ═══════════════════════════════ */}
              {/*  3. Core Patient Info & History */}
              {/* ═══════════════════════════════ */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                {/* Summary */}
                <div className="glass-card" style={{ borderTop: '4px solid var(--accent-amber)' }}>
                  <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    👤 Patient Overview
                  </h3>
                  <ul style={{ paddingLeft: '1.5rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                    <li><strong>Age:</strong> {summary.age || '—'}</li>
                    <li><strong>Complaint:</strong> <span style={{color: 'var(--accent-amber)', fontWeight: 'bold'}}>{summary.chief_complaint || '—'}</span></li>
                    <li><strong>Severity:</strong> {summary.severity || '—'}</li>
                    <li>
                      <strong>Symptoms:</strong>
                      <ul style={{ marginTop: '0.25rem', paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
                        {summary.symptoms?.map((s, idx) => (
                          <li key={idx}>{s.name} ({s.duration})</li>
                        ))}
                      </ul>
                    </li>
                  </ul>
                </div>

                {/* Medical History */}
                <div className="glass-card" style={{ borderTop: '4px solid var(--accent-green)' }}>
                  <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    🩺 Medical History
                  </h3>
                  <ul style={{ paddingLeft: '1.5rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                    <li>
                      <strong>Chronic Conditions:</strong>
                      <div style={{ color: 'var(--text-secondary)' }}>
                        {summary.medical_history?.chronic_conditions?.length > 0
                          ? summary.medical_history.chronic_conditions.join(', ')
                          : 'None reported'}
                      </div>
                    </li>
                    <li>
                      <strong>Allergies:</strong>
                      <div style={{ color: 'var(--text-secondary)' }}>
                        {summary.medical_history?.allergies?.length > 0
                          ? summary.medical_history.allergies.join(', ')
                          : 'None reported'}
                      </div>
                    </li>
                    {summary.additional_notes && (
                      <li>
                        <strong>Additional Notes:</strong>
                        <div style={{ color: 'var(--text-secondary)' }}>{summary.additional_notes}</div>
                      </li>
                    )}
                  </ul>
                </div>
              </div>

              {/* ═══════════════════════════════ */}
              {/*  4. AI Insights               */}
              {/* ═══════════════════════════════ */}
              {analysis && (
                <div className="glass-card" style={{ borderTop: '4px solid var(--accent-blue)', marginBottom: '1rem' }}>
                  <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    🧠 AI Insights & Follow-up
                  </h3>
                  
                  <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>Risk Score:</strong>
                      <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: getRiskClass(analysis.risk_assessment?.risk_level) }}>
                        {analysis.risk_assessment?.risk_score}/100 ({analysis.risk_assessment?.risk_level})
                      </span>
                    </div>
                    {analysis.risk_assessment?.triage_reasoning && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                        "{analysis.risk_assessment.triage_reasoning}"
                      </div>
                    )}
                  </div>

                  {analysis.followup_questions?.length > 0 && (
                    <div>
                      <strong style={{ fontSize: '0.9rem' }}>Suggested Questions:</strong>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                        {analysis.followup_questions.map((q, idx) => (
                          <div key={idx} style={{ padding: '0.5rem', borderLeft: '2px solid var(--accent-blue)', background: 'rgba(0,0,0,0.1)' }}>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{q.question}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{q.rationale}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ═══════════════════════════════ */}
              {/*  Phase 4: Basic Report Analysis */}
              {/* ═══════════════════════════════ */}
              <div className="report-panel glass-card">
                <h3 className="section-title">📄 Analyze Medical Report (Vision AI)</h3>
                <p style={{fontSize: '0.85rem', marginBottom: '1rem', color: 'var(--text-muted)'}}>
                  Upload an X-ray, lab result, or MRI report. The AI will extract key findings. Do NOT use for diagnosis.
                </p>
                <input 
                  type="file" 
                  accept="image/*,application/pdf"
                  onChange={handleUploadReport}
                  disabled={reportUploading}
                  id="report-upload"
                  style={{ display: 'none' }}
                />
                <label htmlFor="report-upload" className="btn btn-secondary" style={{cursor: 'pointer', display: 'inline-block'}}>
                  {reportUploading ? '⏳ Analyzing Vision...' : '📤 Upload Report Image'}
                </label>
                
                {reportResult && (
                  <div style={{marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)'}}>
                    <h4 style={{marginBottom: '0.5rem'}}>Report Type: {reportResult.report_type}</h4>
                    <p style={{fontSize: '0.9rem'}}><strong>Impressions:</strong> {reportResult.impressions}</p>
                    {reportResult.findings?.length > 0 && (
                      <div style={{marginTop: '0.5rem', fontSize: '0.9rem'}}>
                        <strong>Findings:</strong>
                        <ul style={{paddingLeft: '1.5rem', marginTop: '0.25rem'}}>
                          {reportResult.findings.map((f, i) => <li key={i}>{f}</li>)}
                        </ul>
                      </div>
                    )}
                    {reportResult.flagged_abnormalities?.length > 0 && (
                      <div style={{marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--critical)'}}>
                        <strong>🚨 Flagged Abnormalities:</strong>
                        <ul style={{paddingLeft: '1.5rem', marginTop: '0.25rem'}}>
                          {reportResult.flagged_abnormalities.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* ═══════════════════════════════ */}
              {/*  Collapsible: Transcript        */}
              {/* ═══════════════════════════════ */}
              {transcript && (
                <div className="collapsible-panel glass-card">
                  <button
                    className="collapse-toggle"
                    onClick={() => toggleSection(`transcript-${selected.id}`)}
                  >
                    <span className={`toggle-icon ${expandedSections[`transcript-${selected.id}`] ? 'open' : ''}`}>▶</span>
                    {expandedSections[`transcript-${selected.id}`] ? 'Hide' : 'Show'} Raw Transcript
                  </button>
                  {expandedSections[`transcript-${selected.id}`] && (
                    <div className="collapse-body transcript-text">"{transcript}"</div>
                  )}
                </div>
              )}

              {/* ═══════════════════════════════ */}
              {/*  Collapsible: Conversation      */}
              {/* ═══════════════════════════════ */}
              {conversationHistory.length > 0 && (
                <div className="collapsible-panel glass-card">
                  <button
                    className="collapse-toggle"
                    onClick={() => toggleSection(`conv-${selected.id}`)}
                  >
                    <span className={`toggle-icon ${expandedSections[`conv-${selected.id}`] ? 'open' : ''}`}>▶</span>
                    {expandedSections[`conv-${selected.id}`] ? 'Hide' : 'Show'} Conversation History ({conversationHistory.length} turns)
                  </button>
                  {expandedSections[`conv-${selected.id}`] && (
                    <div className="collapse-body conv-history">
                      {conversationHistory.map((turn, tidx) => (
                        <div key={tidx} className={`conv-turn ${turn.role}`}>
                          <strong className={`turn-label ${turn.role}`}>
                            {turn.role === 'ai' ? '🤖 AI' : '🗣️ Patient'}
                          </strong>
                          <span className="turn-text">{turn.text}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </section>
  );
}
