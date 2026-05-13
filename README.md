# EduAI Ghana — AI Teaching Assistant

An AI-powered platform for Ghanaian Primary and JHS teachers to generate lesson plans, exam questions, examples, and explanations — with Ghanaian language translation and text-to-speech.

---

## Architecture

```
eduai/
├── flask_app/          # Frontend & auth (port 5000)
│   ├── app.py          # Flask entry point
│   ├── routes/         # auth, dashboard, documents, generate, settings
│   ├── templates/      # Jinja2 HTML templates
│   └── static/         # CSS, JS, uploads, audio
├── fastapi_app/        # AI backend (port 8000)
│   └── main.py         # RAG, generation, translation, TTS endpoints
├── shared/
│   ├── models/         # SQLAlchemy models (User, Document, Generation)
│   └── utils/
│       ├── rag.py      # ChromaDB ingestion & retrieval
│       ├── llm.py      # Groq, Claude, OpenAI, Gemini
│       └── khaya.py    # Khaya AI translation & TTS
├── run.py              # Start both servers
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone & setup
```bash
cd eduai
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Minimum required:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
KHAYA_API_KEY=your_khaya_key          # for translation & TTS
```

### 3. Run
```bash
python run.py
```

Visit: **http://127.0.0.1:5000**

---

## API Keys

| Service | Key | Purpose | Get it at |
|---------|-----|---------|-----------|
| Groq | `GROQ_API_KEY` | Primary LLM (free tier available) | console.groq.com |
| Anthropic | `ANTHROPIC_API_KEY` | Claude models | console.anthropic.com |
| OpenAI | `OPENAI_API_KEY` | GPT-4o | platform.openai.com |
| Google | `GEMINI_API_KEY` | Gemini 1.5 Pro | aistudio.google.com |
| Khaya AI | `KHAYA_API_KEY` | Ghanaian translation & TTS | ghananlp.org |

---

## Features

- **Auth** — Teacher sign up / login with bcrypt password hashing
- **Knowledge Base** — Upload PDF, DOCX, TXT files per subject; stored in ChromaDB
- **RAG Generation** — Context-aware lesson plans, exam questions, examples, explanations
- **Multi-LLM** — Switch between Groq, Claude, ChatGPT, Gemini
- **Translation** — Translate output to Twi, Ga, Ewe, Dagbani, Dagaare, and more
- **Text-to-Speech** — Listen to translated content in Ghanaian languages
- **History** — View and revisit all past generations

---

## Supported Languages (Khaya AI)

| Code | Language |
|------|----------|
| tw | Twi (Akan) |
| gaa | Ga |
| ee | Ewe |
| dag | Dagbani |
| dga | Dagaare |
| yo | Yoruba |
| ki | Kikuyu |

---

## FastAPI Endpoints

Visit `http://127.0.0.1:8000/docs` for interactive API docs.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Upload & process a document |
| POST | `/generate` | Generate educational content |
| POST | `/translate` | Translate text via Khaya AI |
| POST | `/tts` | Text-to-speech via Khaya AI |
| GET | `/collections/{user_id}` | List user's knowledge collections |
| DELETE | `/collections/{name}` | Delete a collection |
| GET | `/llms` | List LLM availability |
| GET | `/languages` | List supported languages |

---

## Subjects Supported

Mathematics, English Language, Science, Social Studies, Ghanaian Language, Religious & Moral Education, Creative Arts, Physical Education, ICT, French, History, Geography

## Grade Levels

Primary 1–6, JHS 1–3
