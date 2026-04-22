# 🩺 TalkToDoctor — Voice-First AI Medical Intake System

A voice-first AI medical intake system that helps patients describe their symptoms using natural speech, and presents a structured summary to their doctor.

**Core Rule: The AI NEVER diagnoses. It ONLY assists, extracts, and summarizes. The doctor is the final authority.**

## Architecture

```
Voice Input → Whisper API (Transcription) → GPT-4 (Extraction) → Structured JSON → Doctor Dashboard
```

- **Frontend**: React.js (Vite)
- **Backend**: FastAPI (Python)
- **AI/NLP**: OpenAI GPT-4o
- **Speech**: OpenAI Whisper API

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- OpenAI API key

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
cd ..
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/intake` | Upload audio → transcribe → extract → JSON |
| `GET` | `/api/intake/latest` | Get the most recent intake record |
| `GET` | `/api/intake/all` | Get all intake records |
| `GET` | `/health` | Health check |

## Project Structure

```
talktodoctor/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── routers/intake.py     # API endpoints
│   ├── services/
│   │   ├── transcription.py  # Whisper integration
│   │   └── extraction.py     # GPT-4 extraction
│   ├── prompts/
│   │   └── system_prompt.py  # Medical intake prompt
│   ├── models/schemas.py     # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PatientKiosk.jsx    # Voice recording UI
│   │   │   ├── DoctorDashboard.jsx # Summary display
│   │   │   └── Header.jsx
│   │   ├── services/api.js
│   │   ├── App.jsx
│   │   └── index.css
│   └── package.json
└── README.md
```

## License

Private — Not for clinical use without physician verification.
