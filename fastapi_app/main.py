import sys, os, json, asyncio, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from shared.utils.rag import (
    ingest_document, ingest_document_stream,
    retrieve_context, list_user_collections, delete_collection
)
from shared.utils.llm import generate_response, build_educational_prompt, SUPPORTED_LLMS
from shared.utils.khaya import (
    translate_text, text_to_speech,
    get_translation_languages, get_tts_languages, get_tts_speakers,
    get_supported_languages
)

app = FastAPI(title="EduAI Ghana - AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "EduAI Ghana FastAPI"}

# ─── LLM Info ──────────────────────────────────────────────────────────────────
@app.get("/llms")
def get_llms():
    return {"llms": SUPPORTED_LLMS}

# ─── Language Info ─────────────────────────────────────────────────────────────
@app.get("/languages")
def get_languages():
    return {"languages": get_translation_languages()}

@app.get("/tts-languages")
def get_tts_language_list():
    return {"languages": get_tts_languages(), "speakers": get_tts_speakers()}

# ─── Document Ingestion (silent, kept for internal use) ───────────────────────
class IngestResponse(BaseModel):
    success: bool
    collection_name: str
    chunk_count: int
    message: str

@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    subject: str = Form(...),
    grade_level: str = Form("")
):
    allowed = ['.pdf', '.docx', '.doc', '.txt', '.md', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type not supported. Allowed: {allowed}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_document(tmp_path, user_id, subject, grade_level)
        return IngestResponse(
            success=True,
            collection_name=result["collection_name"],
            chunk_count=result["chunk_count"],
            message=f"Document ingested: {result['chunk_count']} chunks stored."
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        os.unlink(tmp_path)


# ─── Streaming Ingest with SSE progress ───────────────────────────────────────
@app.post("/ingest/stream")
async def ingest_stream(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    subject: str = Form(...),
    grade_level: str = Form("")
):
    """
    SSE endpoint — streams each RAG ingestion step as a Server-Sent Event.
    Each event is a JSON object:
    { step, total_steps, label, detail, progress, done, error, [collection_name, chunk_count] }
    """
    allowed = ['.pdf', '.docx', '.doc', '.txt', '.md', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type not supported. Allowed: {allowed}")

    # Save to temp file — must read the whole upload before streaming starts
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    async def event_generator():
        try:
            loop = asyncio.get_event_loop()
            # Run the synchronous generator in a thread pool so it doesn't block
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                gen = ingest_document_stream(tmp_path, user_id, subject, grade_level)
                for step_data in gen:
                    # Format as SSE
                    payload = json.dumps(step_data)
                    yield f"data: {payload}\n\n"
                    # Tiny sleep to let the event loop breathe and flush to client
                    await asyncio.sleep(0.05)
        except Exception as e:
            error_payload = json.dumps({
                "step": -1, "label": "Server error",
                "detail": str(e), "progress": 0,
                "done": True, "error": str(e)
            })
            yield f"data: {error_payload}\n\n"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
            "Connection": "keep-alive",
        }
    )


# ─── Collections ───────────────────────────────────────────────────────────────
@app.get("/collections/{user_id}")
def get_collections(user_id: int):
    return {"collections": list_user_collections(user_id)}

@app.delete("/collections/{collection_name}")
def remove_collection(collection_name: str):
    try:
        delete_collection(collection_name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))

# ─── Generate ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    user_id: int
    subject: str
    grade_level: str
    topic: str
    generation_type: str
    llm_choice: Optional[str] = "groq"
    extra_instructions: Optional[str] = ""

class GenerateResponse(BaseModel):
    success: bool
    content: str
    llm_used: str

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    valid_types = ["lesson_plan", "exam_questions", "examples", "explanation"]
    if req.generation_type not in valid_types:
        raise HTTPException(400, f"generation_type must be one of {valid_types}")

    context = retrieve_context(req.topic, req.user_id, req.subject)
    prompt = build_educational_prompt(
        req.generation_type, req.topic, req.grade_level,
        req.subject, context, req.extra_instructions
    )
    try:
        content = generate_response(prompt, req.llm_choice or "groq")
        return GenerateResponse(success=True, content=content, llm_used=req.llm_choice or "groq")
    except Exception as e:
        raise HTTPException(500, str(e))

# ─── Translation ──────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str
    source_lang: Optional[str] = "en"
    target_lang: str

@app.post("/translate")
async def translate(req: TranslateRequest):
    result = translate_text(req.text, req.source_lang, req.target_lang)
    if not result["success"]:
        raise HTTPException(500, result.get("error", "Translation failed"))
    return result

# ─── TTS ──────────────────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    language: str
    speaker_id: Optional[str] = "female"
    audio_format: Optional[str] = "mp3"

@app.post("/tts")
async def tts(req: TTSRequest):
    result = text_to_speech(req.text, req.language, req.speaker_id or "female", req.audio_format or "mp3")
    if not result["success"]:
        raise HTTPException(500, result.get("error", "TTS failed"))
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
