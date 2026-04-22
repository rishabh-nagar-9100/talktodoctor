# 🩺 TalkToDoctor — Enterprise AI Medical Intake & Queue System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-FF4B4B.svg)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-Private-lightgrey.svg)](#)

A production-ready, voice-first AI medical intake system designed for high-load clinics and hospitals. TalkToDoctor streamlines patient documentation by converting natural multilingual speech into structured, actionable clinical insights.

> **CRITICAL RULE**: The AI NEVER diagnoses. It ONLY assists, extracts, and summarizes. The doctor is the final authority in all clinical decisions.

---

## 🚀 Key Features

### 1. 🎙️ Multilingual Voice-First Intake
- **Zero-Type Interface**: Patients interact solely via voice, making it accessible for all literacy levels.
- **Natural Language Support**: Full support for Hindi, English, Tamil, Telugu, and more.
- **AI-Guided Conversation**: Dynamic follow-up questions to ensure a complete symptom profile is captured.

### 2. 🏥 Production-Grade Queue Management
- **Token Generation**: Automated clinic tokens (e.g., `G-01`, `U-05`) assigned based on urgency.
- **Smart Triage**: Deterministic risk calculation flags critical symptoms (Chest Pain, Shortness of Breath) for immediate attention.
- **SMS Notifications**: Automated SMS alerts for token confirmation and "Next Turn" notifications.

### 3. 👨‍⚕️ Clinical Assist Dashboard
- **Instant Summaries**: Doctors scan patient cases in <10 seconds with high-fidelity structured data.
- **Risk Assessment**: Deterministic scoring (Independent of LLM) for clinical safety.
- **AI Follow-up Suggestions**: Targeted questions generated per-patient to guide the consultation.
- **EHR Integration**: Mock FHIR/HL7 export for integration with hospital information systems.

### 4. 📊 Analytics & Insights
- **Clinical Trends**: Real-time tracking of top symptoms and severity distribution.
- **Efficiency Metrics**: Estimated physician time saved and patient throughput volume.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React (Vite), Lucide Icons, CSS3 (Glassmorphism) |
| **Backend** | FastAPI (Python), Uvicorn |
| **Database** | Supabase (PostgreSQL) |
| **Speech-to-Text** | OpenAI Whisper (via Groq) |
| **Clinical Engine** | Llama 3.3 70B / GPT-4o (via Groq) |
| **TTS** | OpenAI TTS-1 |

---

## 📋 Database Schema (Supabase)

The system uses a relational PostgreSQL schema designed for PHI security and scalability:
- `patients`: Demographics and contact info.
- `intake_sessions`: Lifecycle of individual patient interactions.
- `conversation_turns`: Full transcript (Patient + AI).
- `medical_summaries`: Structured symptoms, history, and risk levels.
- `queue_items`: Real-time status (`WAITING`, `IN_CONSULTATION`, `COMPLETED`).

---

## ⚙️ Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- [Supabase Project](https://supabase.com/) (Run the provided SQL in the SQL Editor)
- [Groq API Key](https://console.groq.com/)

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Update .env with your GROQ_API_KEY, SUPABASE_URL, and SUPABASE_KEY
python -m uvicorn backend.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🔌 API Reference

| Category | Method | Endpoint | Description |
|---|---|---|---|
| **Intake** | `POST` | `/api/conversation/start` | Initialize new session |
| **Intake** | `POST` | `/api/conversation/respond` | Process voice turn |
| **Queue** | `POST` | `/api/queue/join` | Join clinic queue |
| **Queue** | `GET` | `/api/queue/live` | Live dashboard feed |
| **Doctor** | `POST` | `/api/doctor/analyze/{id}` | Generate clinical intelligence |
| **Analytics** | `GET` | `/api/analytics/dashboard` | System-wide metrics |

---

## 📂 Project Structure

```text
talktodoctor/
├── backend/
│   ├── db/               # Supabase Client
│   ├── models/           # Pydantic Schemas
│   ├── routers/          # Modular API Routes (Intake, Queue, Doctor)
│   ├── services/         # Business Logic (Transcription, Extraction, Queue)
│   └── prompts/          # Clinical Prompt Engineering
├── frontend/
│   ├── src/
│   │   ├── components/   # PatientKiosk, DoctorDashboard, Analytics
│   │   └── services/     # API Integration
└── .env                  # Global Configuration
```

---

## 🔒 Security & Privacy
- **Row Level Security (RLS)**: Enforced at the Supabase layer to ensure data isolation.
- **No Local Storage**: Sensitive medical data is never stored on the local client.
- **Audit Logs**: Every status change in the queue is timestamped and recorded.

---

## 📜 License
Private. Developed for healthcare optimization. Not for independent clinical diagnosis.
