/**
 * API service for communicating with the TalkToDoctor backend.
 *
 * Phase 1: Single-shot audio intake
 * Phase 2: Multi-turn conversation with TTS
 *
 * All backend calls go through this module for centralized
 * error handling and configuration.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ══════════════════════════════════════════════
//  Phase 1 — Single-Shot Intake
// ══════════════════════════════════════════════

/**
 * Submit a recorded audio blob to the backend for processing.
 *
 * Pipeline: Audio → Whisper (transcription) → GPT-4 (extraction) → JSON
 *
 * @param {Blob} audioBlob - The recorded audio blob from MediaRecorder.
 * @returns {Promise<Object>} The IntakeResponse with transcript, summary, and disclaimer.
 */
export async function submitAudio(audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'patient_audio.webm');

  const response = await fetch(`${API_BASE_URL}/api/intake`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch the most recent patient intake record.
 *
 * @returns {Promise<Object>} The latest intake record with id, timestamp, and data.
 */
export async function getLatestIntake() {
  const response = await fetch(`${API_BASE_URL}/api/intake/latest`);

  if (!response.ok) {
    if (response.status === 404) return null;
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch all patient intake records.
 *
 * @returns {Promise<Array>} Array of intake records, newest first.
 */
export async function getAllIntakes() {
  const response = await fetch(`${API_BASE_URL}/api/intake/all`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

// ══════════════════════════════════════════════
//  Phase 2 — Multi-Turn Conversation
// ══════════════════════════════════════════════

/**
 * Start a new conversation session.
 *
 * Returns the session ID, the AI's opening question, and TTS audio.
 *
 * @returns {Promise<Object>} ConversationStartResponse
 */
export async function startConversation(language = 'English') {
  const formData = new FormData();
  formData.append('language', language);

  const response = await fetch(`${API_BASE_URL}/api/conversation/start`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Send the patient's audio response in an active conversation.
 *
 * Returns the AI's next action (follow-up question, confirmation, or completion)
 * along with optional TTS audio.
 *
 * @param {string} sessionId - Active session ID.
 * @param {Blob} audioBlob - Patient's recorded audio.
 * @returns {Promise<Object>} ConversationResponse
 */
export async function sendConversationAudio(sessionId, audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'patient_audio.webm');
  formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE_URL}/api/conversation/respond`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Get the current state of a conversation session.
 *
 * @param {string} sessionId - Session ID.
 * @returns {Promise<Object>} Session state with turns and summary.
 */
export async function getConversationState(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/conversation/${sessionId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

// ══════════════════════════════════════════════
//  Phase 3 — Doctor Efficiency System
// ══════════════════════════════════════════════

/**
 * Request doctor analysis for a specific intake record.
 *
 * Returns: risk assessment (deterministic), critical symptom flags,
 * and AI-suggested follow-up questions.
 *
 * @param {number} intakeId - The intake record ID.
 * @returns {Promise<Object>} DoctorAnalysis with risk, flags, and questions.
 */
export async function analyzeIntake(intakeId) {
  const response = await fetch(`${API_BASE_URL}/api/doctor/analyze/${intakeId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch the list of critical symptom keywords used for frontend highlighting.
 *
 * @returns {Promise<Object>} { critical_keywords: string[] }
 */
export async function getRiskKeywords() {
  const response = await fetch(`${API_BASE_URL}/api/doctor/risk-keywords`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

// ══════════════════════════════════════════════
//  Phase 4 — Advanced AI & Data (Patients & Reports)
// ══════════════════════════════════════════════

export async function getPatients() {
  const response = await fetch(`${API_BASE_URL}/api/patients`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function getPatientHistory(patientId) {
  const response = await fetch(`${API_BASE_URL}/api/patients/${patientId}/history`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function analyzeReport(file, patientId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('patient_id', patientId);

  const response = await fetch(`${API_BASE_URL}/api/reports/analyze`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

// ══════════════════════════════════════════════
//  Phase 5 — Scaling & Optimization (Analytics & Integrations)
// ══════════════════════════════════════════════

export async function getAnalyticsDashboard() {
  const response = await fetch(`${API_BASE_URL}/api/analytics/dashboard`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function exportToEHR(intakeId) {
  const response = await fetch(`${API_BASE_URL}/api/integrations/ehr/export/${intakeId}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

// ══════════════════════════════════════════════
//  Phase 7 — Queue & Notifications
// ══════════════════════════════════════════════

export async function joinQueue(intakeId, phoneNumber) {
  const response = await fetch(`${API_BASE_URL}/api/queue/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intake_id: intakeId, phone_number: phoneNumber }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function getLiveQueue() {
  const response = await fetch(`${API_BASE_URL}/api/queue/live`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function callPatient(queueId) {
  const response = await fetch(`${API_BASE_URL}/api/queue/${queueId}/call`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function completePatient(queueId) {
  const response = await fetch(`${API_BASE_URL}/api/queue/${queueId}/complete`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

export async function skipPatient(queueId) {
  const response = await fetch(`${API_BASE_URL}/api/queue/${queueId}/skip`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }
  return response.json();
}
