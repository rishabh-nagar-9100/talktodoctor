/**
 * PatientKiosk Component — Phase 2: Conversational Intake
 *
 * Transformed from single-shot to a multi-turn chat interface.
 * - AI speaks follow-up questions via TTS
 * - Patient records audio responses
 * - Chat bubble history shows the conversation
 * - Confirmation step before finalizing
 * - Auto-records after AI finishes speaking
 *
 * States: idle → starting → listening_to_ai → recording → processing →
 *         (loop) → confirming → done | error
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { startConversation, sendConversationAudio } from '../services/api';
import './PatientKiosk.css';

// Maximum turns shown in the progress indicator
const MAX_TURNS = 5;

export default function PatientKiosk({ onIntakeComplete }) {
  // ── State ──
  const [phase, setPhase] = useState('idle');
  // idle | starting | listening_to_ai | recording | processing | confirming | done | error
  const [sessionId, setSessionId] = useState(null);
  const sessionIdRef = useRef(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [turnNumber, setTurnNumber] = useState(0);
  const [language, setLanguage] = useState('English');
  const [partialSummary, setPartialSummary] = useState(null);
  const [finalSummary, setFinalSummary] = useState(null);
  const [intakeId, setIntakeId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [queueToken, setQueueToken] = useState(null);
  const [waitMins, setWaitMins] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  const [timer, setTimer] = useState(0);

  // ── Refs ──
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);
  const streamRef = useRef(null);
  const chatEndRef = useRef(null);
  const audioPlayerRef = useRef(null);

  // ── Scroll chat to bottom on new messages ──
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, phase]);

  // ── Cleanup on unmount ──
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
    };
  }, []);

  // ── Format timer as MM:SS ──
  const formatTime = (s) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  // ══════════════════════════════════════════
  //  Start Conversation
  // ══════════════════════════════════════════
  const handleStart = useCallback(async (selectedLang) => {
    if (!phoneNumber || phoneNumber.length < 5) {
      setErrorMsg('Please enter your phone number or email first.');
      return;
    }

    setLanguage(selectedLang);
    setPhase('starting');
    setErrorMsg('');
    setChatHistory([]);

    try {
      const response = await startConversation(selectedLang);
      setSessionId(response.session_id);
      sessionIdRef.current = response.session_id;
      setTurnNumber(1);

      // Add AI's opening question to chat
      setChatHistory([{
        role: 'ai',
        text: response.ai_question,
      }]);

      // Play TTS audio if available
      if (response.audio_base64) {
        await playTTSAudio(response.audio_base64);
      } else {
        // No audio — go straight to recording
        setPhase('recording');
        await startMicRecording();
      }
    } catch (err) {
      console.error('Start conversation error:', err);
      setPhase('error');
      setErrorMsg(err.message || 'Failed to start conversation.');
    }
  }, [phoneNumber]);

  // ══════════════════════════════════════════
  //  Play TTS Audio
  // ══════════════════════════════════════════
  const playTTSAudio = useCallback(async (base64Audio) => {
    setPhase('listening_to_ai');

    try {
      // Decode base64 to audio blob
      const audioBytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const audioBlob = new Blob([audioBytes], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;

      // When the AI finishes speaking, auto-start recording
      audio.onended = async () => {
        URL.revokeObjectURL(audioUrl);
        audioPlayerRef.current = null;
        // Auto-start recording after AI speaks
        setPhase('recording');
        await startMicRecording();
      };

      audio.onerror = async () => {
        URL.revokeObjectURL(audioUrl);
        console.warn('TTS playback failed, starting recording anyway');
        setPhase('recording');
        await startMicRecording();
      };

      await audio.play();
    } catch (err) {
      console.warn('TTS playback error:', err);
      // Fallback: start recording without audio
      setPhase('recording');
      await startMicRecording();
    }
  }, []);

  // ══════════════════════════════════════════
  //  Microphone Recording
  // ══════════════════════════════════════════
  const startMicRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 44100 }
      });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = handleRecordingComplete;

      mediaRecorder.start(250);
      setPhase('recording');
      setTimer(0);

      timerIntervalRef.current = setInterval(() => {
        setTimer((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Mic error:', err);
      setPhase('error');
      setErrorMsg(
        err.name === 'NotAllowedError'
          ? 'Microphone access denied. Please allow microphone access.'
          : `Microphone error: ${err.message}`
      );
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  // ══════════════════════════════════════════
  //  Handle Completed Recording
  // ══════════════════════════════════════════
  const handleRecordingComplete = async () => {
    setPhase('processing');

    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

      if (audioBlob.size === 0) {
        throw new Error('Recording is empty. Please try again.');
      }

      // Send to backend
      const currentSessionId = sessionIdRef.current;
      const response = await sendConversationAudio(currentSessionId, audioBlob);

      // Add patient's transcript to chat
      if (response.patient_transcript) {
        setChatHistory(prev => [...prev, {
          role: 'patient',
          text: response.patient_transcript,
        }]);
      }

      setTurnNumber(response.turn_number);
      setLanguage(response.language || 'English');

      // Handle the AI's decision
      const action = response.action;

      if (action === 'ask_followup') {
        // Add AI's follow-up to chat
        setChatHistory(prev => [...prev, {
          role: 'ai',
          text: response.ai_text,
        }]);

        // Play TTS and then auto-record
        if (response.audio_base64) {
          await playTTSAudio(response.audio_base64);
        } else {
          setPhase('recording');
          await startMicRecording();
        }

      } else if (action === 'confirm') {
        // Add AI's confirmation to chat
        setChatHistory(prev => [...prev, {
          role: 'ai',
          text: response.ai_text,
        }]);

        setPartialSummary(response.partial_summary);
        setPhase('confirming');

        // Play the confirmation audio
        if (response.audio_base64) {
          // Don't auto-record after confirmation — show buttons instead
          playConfirmationAudio(response.audio_base64);
        }

      } else if (action === 'complete') {
        setFinalSummary(response.final_summary);
        setIntakeId(response.intake_id);
        setPhase('processing'); // Keep processing while joining queue

        try {
          const { joinQueue } = await import('../services/api');
          const res = await joinQueue(response.intake_id, phoneNumber);
          
          setQueueToken(res.token);
          setWaitMins(res.expected_wait_mins);
          setPhase('done');

          if (onIntakeComplete) {
            onIntakeComplete({
              summary: response.final_summary,
              conversation_history: response.conversation_history,
            });
          }
        } catch (err) {
          console.error('Queue join error:', err);
          setPhase('error');
          setErrorMsg('Failed to generate token. Please inform the receptionist.');
        }
      }

    } catch (err) {
      console.error('Processing error:', err);
      setPhase('error');
      setErrorMsg(err.message || 'Failed to process your response.');
    }
  };

  // Play confirmation audio without auto-recording
  const playConfirmationAudio = async (base64Audio) => {
    try {
      const audioBytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const audioBlob = new Blob([audioBytes], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(audioUrl); audioPlayerRef.current = null; };
      await audio.play();
    } catch (err) {
      console.warn('Confirmation TTS error:', err);
    }
  };

  // ══════════════════════════════════════════
  //  Confirmation Handlers
  // ══════════════════════════════════════════
  const handleConfirmYes = async () => {
    // Record a short "yes" — or we can send a text confirmation
    // For simplicity, start recording so patient can say "yes"
    setPhase('recording');
    await startMicRecording();
  };

  const handleConfirmNo = async () => {
    // Add a "no" response and let patient clarify
    setChatHistory(prev => [...prev, {
      role: 'patient',
      text: '(Needs clarification)',
    }]);
    setPhase('recording');
    await startMicRecording();
  };

  // handleJoinQueue removed since it's auto-called

  // ══════════════════════════════════════════
  //  Reset
  // ══════════════════════════════════════════
  const resetKiosk = () => {
    setPhase('idle');
    setSessionId(null);
    sessionIdRef.current = null;
    setChatHistory([]);
    setTurnNumber(0);
    setLanguage('English');
    setPartialSummary(null);
    setFinalSummary(null);
    setIntakeId(null);
    setPhoneNumber('');
    setQueueToken(null);
    setWaitMins(0);
    setErrorMsg('');
    setTimer(0);
  };

  // ══════════════════════════════════════════
  //  Render
  // ══════════════════════════════════════════

  // ── Idle: Start Screen ──
  if (phase === 'idle') {
    return (
      <section className="kiosk" id="patient-kiosk">
        <div className="start-screen">
          <h1>Tell Us How You Feel</h1>
          <p>
            Please enter your phone number or email, then choose your preferred language to start speaking with our AI assistant.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '2rem 0' }}>
            <input 
              type="text" 
              placeholder="Enter Mobile Number or Email" 
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              style={{
                padding: '1rem 1.5rem', 
                fontSize: '1.2rem', 
                borderRadius: '8px', 
                border: '1px solid var(--border-subtle)',
                background: 'rgba(0,0,0,0.3)',
                color: 'white',
                textAlign: 'center',
                width: '100%',
                maxWidth: '400px'
              }}
            />
            {errorMsg && <div style={{color: 'var(--accent-red)', marginTop: '0.5rem', fontSize: '1rem'}}>{errorMsg}</div>}
          </div>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={() => handleStart('English')}
              style={{ fontSize: '1.2rem', padding: '1rem 2rem' }}
            >
              🇬🇧 English
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleStart('Hindi')}
              style={{ fontSize: '1.2rem', padding: '1rem 2rem', background: 'linear-gradient(135deg, var(--accent-amber), hsl(20, 90%, 55%))', boxShadow: '0 4px 16px var(--accent-amber-glow)' }}
            >
              🇮🇳 Hindi
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleStart('Tamil')}
              style={{ fontSize: '1.2rem', padding: '1rem 2rem', background: 'linear-gradient(135deg, var(--accent-purple), hsl(290, 70%, 55%))' }}
            >
              🇮🇳 Tamil
            </button>
          </div>
        </div>
      </section>
    );
  }

  // ── Starting: Loading screen ──
  if (phase === 'starting') {
    return (
      <section className="kiosk" id="patient-kiosk">
        <div className="start-screen">
          <h1>Setting Up...</h1>
          <p className="status-processing">Preparing your session</p>
        </div>
      </section>
    );
  }

  // ── Active Conversation ──
  return (
    <section className="kiosk" id="patient-kiosk">

      {/* ── Turn Progress ── */}
      <div className="turn-progress">
        <div className="turn-dots">
          {Array.from({ length: MAX_TURNS }, (_, i) => (
            <span
              key={i}
              className={`turn-dot ${
                i < turnNumber ? 'filled' : ''
              } ${i === turnNumber - 1 && phase === 'recording' ? 'active' : ''}`}
            />
          ))}
        </div>
        <span>Turn {turnNumber} of {MAX_TURNS}</span>
        {language !== 'English' && (
          <span className="lang-badge">🌐 {language}</span>
        )}
      </div>

      {/* ── Chat Area ── */}
      <div className="chat-area">
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`chat-bubble ${msg.role}`}>
            <div className={`bubble-label ${msg.role === 'ai' ? 'ai-label' : 'patient-label'}`}>
              {msg.role === 'ai' ? '🤖 AI Assistant' : '🗣️ You'}
            </div>
            {msg.text}
          </div>
        ))}

        {/* AI Speaking Indicator */}
        {phase === 'listening_to_ai' && (
          <div className="ai-speaking">
            <div className="waveform">
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
            </div>
            AI is speaking...
          </div>
        )}

        {/* Processing Indicator */}
        {phase === 'processing' && (
          <div className="ai-speaking">
            <div className="waveform">
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
              <span className="waveform-bar"></span>
            </div>
            Processing your response...
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={chatEndRef} />
      </div>

      {/* ── Confirmation Card ── */}
      {phase === 'confirming' && partialSummary && (
        <div className="confirm-card glass-card">
          <h3>📋 Please Confirm</h3>
          <div className="confirm-summary">
            <div className="confirm-field">
              <span className="confirm-label">Age:</span>
              <span className="confirm-value">{partialSummary.age || 'Not specified'}</span>
            </div>
            <div className="confirm-field">
              <span className="confirm-label">Severity:</span>
              <span className="confirm-value">{partialSummary.severity || 'Not assessed'}</span>
            </div>
            {partialSummary.symptoms?.map((s, i) => (
              <div key={i} className="confirm-field">
                <span className="confirm-label">Symptom {i + 1}:</span>
                <span className="confirm-value">
                  {s.name} {s.duration !== 'Not specified' ? `(${s.duration})` : ''}
                </span>
              </div>
            ))}
          </div>
          <div className="confirm-actions">
            <button
              id="confirm-yes-btn"
              className="btn btn-confirm"
              onClick={handleConfirmYes}
            >
              ✅ Yes, that's correct
            </button>
            <button
              id="confirm-no-btn"
              className="btn btn-clarify"
              onClick={handleConfirmNo}
            >
              ✏️ Let me clarify
            </button>
          </div>
        </div>
      )}

      {/* Collecting Phone section removed, happening on start */}

      {/* ── Completion Card ── */}
      {phase === 'done' && (
        <div className="complete-card glass-card">
          <div className="complete-icon">✅</div>
          <h2>Thank You!</h2>
          <div style={{
            background: 'rgba(0,0,0,0.2)', 
            padding: '1.5rem', 
            borderRadius: '12px',
            margin: '1rem 0',
            border: '1px solid var(--accent-green)'
          }}>
            <h3 style={{margin: 0, fontSize: '1rem', color: 'var(--text-secondary)'}}>Your Token Number</h3>
            <div style={{fontSize: '3rem', fontWeight: 'bold', color: 'var(--accent-green)', letterSpacing: '2px', margin: '0.5rem 0'}}>
              {queueToken}
            </div>
            <p style={{margin: 0, fontSize: '1rem'}}>
              Estimated Wait: <strong>~{waitMins} mins</strong>
            </p>
          </div>
          <p style={{fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1.5rem'}}>
            We've sent an update to {phoneNumber} with a live tracking link. Please take a seat.
          </p>
          <button id="new-conversation-btn" className="btn btn-primary" onClick={resetKiosk}>
            🎤 Next Patient
          </button>
        </div>
      )}

      {/* ── Error Banner ── */}
      {phase === 'error' && errorMsg && (
        <div className="error-banner">
          ❌ {errorMsg}
          <button className="btn btn-primary" onClick={resetKiosk} style={{ marginLeft: 'auto', padding: '6px 16px', fontSize: '0.8rem' }}>
            Try Again
          </button>
        </div>
      )}

      {/* ── Input Area (recording controls) ── */}
      {(phase === 'recording' || phase === 'listening_to_ai' || phase === 'processing') && (
        <div className="input-area">
          <p className={`input-status ${
            phase === 'recording' ? 'status-recording' :
            phase === 'listening_to_ai' ? 'status-listening' :
            'status-processing'
          }`}>
            {phase === 'recording' && 'Listening... speak clearly'}
            {phase === 'listening_to_ai' && 'AI is speaking — please listen'}
            {phase === 'processing' && 'Processing your response...'}
          </p>

          <div className="mic-section">
            {phase === 'recording' && (
              <span className="mic-timer">{formatTime(timer)}</span>
            )}
            <button
              id="mic-btn"
              className={`mic-btn ${phase === 'recording' ? 'recording' : ''}`}
              onClick={phase === 'recording' ? stopRecording : null}
              disabled={phase !== 'recording'}
              aria-label={phase === 'recording' ? 'Stop recording' : 'Waiting'}
            >
              {phase === 'recording' ? '⏹️' : '🎤'}
            </button>
            {phase === 'recording' && (
              <button
                id="stop-btn"
                className="btn btn-danger"
                onClick={stopRecording}
                style={{ padding: '8px 20px', fontSize: '0.85rem' }}
              >
                ⏹ Done
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
