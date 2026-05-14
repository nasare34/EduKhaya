import os
import requests
import hashlib
import time
from dotenv import load_dotenv

from pathlib import Path as _Path
_env_path = _Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# ─── Separate API keys — each Khaya API has its own subscription key ──────────
# Get them from: https://translation.ghananlp.org → Profile → Subscriptions
# Each API (TTS, Translation) is subscribed to separately and has its own key.
KHAYA_TTS_KEY       = os.getenv("KHAYA_TTS_KEY", "")
KHAYA_TRANSLATE_KEY = os.getenv("KHAYA_TRANSLATE_KEY", "")

# ─── Endpoint URLs ────────────────────────────────────────────────────────────
KHAYA_BASE_URL = "https://translation-api.ghananlp.org"
TTS_V2_URL     = f"{KHAYA_BASE_URL}/tts/v2/synthesize"
TRANSLATE_URL  = f"{KHAYA_BASE_URL}/v2/translate"

# ─── Translation API v2 ───────────────────────────────────────────────────────
# POST /v2/translate
# Header: Ocp-Apim-Subscription-Key: <KHAYA_TRANSLATE_KEY>
# Body:   { "in": "text", "lang": "en-tw" }
# Response: raw JSON string e.g. "Nkyerɛaseɛ nkyerɛwee"
# Max: 1000 characters per request
TRANSLATION_LANGUAGES = {
    "en":  "English",
    "tw":  "Twi",
    "ee":  "Ewe",
    "gaa": "Ga",
    "fat": "Fante",
    "yo":  "Yoruba",
    "dag": "Dagbani",
    "ki":  "Kikuyu",
    "gur": "Gurune",
    "luo": "Luo",
    "mer": "Kimeru",
    "kus": "Kusaal",
}

# ─── TTS API v2 ───────────────────────────────────────────────────────────────
# POST /tts/v2/synthesize
# Header: Ocp-Apim-Subscription-Key: <KHAYA_TTS_KEY>
# Body:   { "text": "...", "language": "twi", "speaker_id": "female",
#           "stream": false, "format": "mp3" }
# Response: binary audio bytes
# Available speakers: male_low, male_high, female
TTS_LANGUAGES = {
    "ada": "Adangme",
    "atw": "Akuapem Twi",
    "twi": "Asante Twi",
    "dag": "Dagbani",
    "dga": "Dagaare",
    "ewe": "Ewe",
    "fat": "Fante",
    "fra": "French",
    "gaa": "Ga",
    "gjn": "Gonja",
    "gur": "Gurene",
    "hau": "Hausa",
    "ibo": "Igbo",
    "xsm": "Kasem",
    "kik": "Kikuyu",
    "xon": "Konkomba (Likpakpaanl)",
    "lxn": "Konkomba (Likoonli)",
    "kri": "Krio",
    "kus": "Kusaal",
    "luo": "Luo",
    "maw": "Mampruli",
    "men": "Mende",
    "mer": "Meru/Kimeru",
    "nzi": "Nzema",
    "pcm": "Pidgin",
    "sna": "Shona",
    "swa": "Swahili",
    "tem": "Temne",
    "wlx": "Wali",
    "wol": "Wolof",
    "yor": "Yoruba",
}

TTS_SPEAKERS = ["male_low", "male_high", "female"]

# Map translation codes → TTS codes (they use different naming conventions)
TRANSLATION_TO_TTS_CODE = {
    "tw":  "twi",
    "ee":  "ewe",
    "gaa": "gaa",
    "fat": "fat",
    "yo":  "yor",
    "dag": "dag",
    "ki":  "kik",
    "gur": "gur",
    "luo": "luo",
    "mer": "mer",
    "kus": "kus",
    "en":  "",
}


def _translate_headers():
    """Headers for Translation API — uses KHAYA_TRANSLATE_KEY."""
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": KHAYA_TRANSLATE_KEY,
    }

def _tts_headers():
    """Headers for TTS API — uses KHAYA_TTS_KEY (different subscription)."""
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": KHAYA_TTS_KEY,
    }


def _chunk_text(text: str, max_chars: int = 950) -> list:
    """
    Split text into chunks preserving structure.
    Priority: split at double newlines (section breaks) first,
    then at single newlines, then at sentence boundaries.
    This keeps numbered lists and section headers together.
    """
    if len(text) <= max_chars:
        return [text]

    # First try to split at paragraph/section boundaries (blank lines)
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""

    for para in paragraphs:
        # If adding this paragraph stays under limit, add it
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + '\n\n' + para).strip() if current else para
        else:
            # Save current chunk if non-empty
            if current:
                chunks.append(current)
            # If the paragraph itself is too long, split at line boundaries
            if len(para) > max_chars:
                lines = para.split('\n')
                sub_current = ""
                for line in lines:
                    if len(sub_current) + len(line) + 1 <= max_chars:
                        sub_current = (sub_current + '\n' + line).strip() if sub_current else line
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = line
                if sub_current:
                    current = sub_current
                else:
                    current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


# ─── Translation ──────────────────────────────────────────────────────────────

def translate_text(text: str, source_lang: str = "en", target_lang: str = "tw") -> dict:
    """
    Text-to-text translation via Khaya AI Translation API v2.
    Uses KHAYA_TRANSLATE_KEY (separate from TTS key).
    """
    if target_lang == "en" or target_lang == source_lang:
        return {"success": True, "translated_text": text, "language": "en"}

    if not KHAYA_TRANSLATE_KEY:
        return {
            "success": False,
            "error": "KHAYA_TRANSLATE_KEY not set. Add it to your .env file (separate from KHAYA_TTS_KEY).",
            "translated_text": text
        }

    if target_lang not in TRANSLATION_LANGUAGES:
        return {
            "success": False,
            "error": f"Language '{target_lang}' not supported. Supported: {list(TRANSLATION_LANGUAGES.keys())}",
            "translated_text": text
        }

    chunks = _chunk_text(text, max_chars=950)
    translated_chunks = []

    try:
        for chunk in chunks:
            resp = requests.post(
                TRANSLATE_URL,
                json={"in": chunk, "lang": f"{source_lang}-{target_lang}"},
                headers=_translate_headers(),
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            translated = result if isinstance(result, str) else str(result)
            # Remove any stars the translation API might introduce
            translated = translated.replace('***', '').replace('**', '').replace('*', '')
            translated_chunks.append(translated)

        # Rejoin with double newlines to preserve section structure
        return {
            "success": True,
            "translated_text": "\n\n".join(translated_chunks),
            "language": target_lang,
            "language_name": TRANSLATION_LANGUAGES.get(target_lang, target_lang)
        }

    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"Translation API {e.response.status_code}: {e.response.text}",
            "translated_text": text
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "translated_text": text}


# ─── Text-to-Speech ───────────────────────────────────────────────────────────

def text_to_speech(
    text: str,
    language: str,
    speaker_id: str = "female",
    audio_format: str = "mp3"
) -> dict:
    """
    Text-to-speech via Khaya AI TTS API v2.
    Uses KHAYA_TTS_KEY (separate from translation key).
    `language` accepts both translation codes (tw) and TTS codes (twi) — auto-mapped.
    """
    if not KHAYA_TTS_KEY:
        return {
            "success": False,
            "error": "KHAYA_TTS_KEY not set. Add it to your .env file (separate from KHAYA_TRANSLATE_KEY).",
            "audio_url": None
        }

    # Auto-map translation code → TTS code if needed
    tts_lang = TRANSLATION_TO_TTS_CODE.get(language, language)

    if not tts_lang:
        return {
            "success": False,
            "error": f"TTS not available for language '{language}'.",
            "audio_url": None
        }

    if tts_lang not in TTS_LANGUAGES:
        return {
            "success": False,
            "error": f"TTS language code '{tts_lang}' not supported. Supported: {list(TTS_LANGUAGES.keys())}",
            "audio_url": None
        }

    if speaker_id not in TTS_SPEAKERS:
        speaker_id = "female"

    if audio_format not in ("wav", "mp3", "ogg"):
        audio_format = "mp3"

    tts_text = text[:1500]

    try:
        resp = requests.post(
            TTS_V2_URL,
            json={
                "text": tts_text,
                "language": tts_lang,
                "speaker_id": speaker_id,
                "stream": False,
                "format": audio_format
            },
            headers=_tts_headers(),   # ← TTS key, not translation key
            timeout=60
        )
        resp.raise_for_status()

        # Use AUDIO_FOLDER env var if set (Render), otherwise fall back to static/audio
        audio_dir = os.getenv(
            "AUDIO_FOLDER",
            os.path.join(os.path.dirname(__file__), "../../flask_app/static/audio")
        )
        os.makedirs(audio_dir, exist_ok=True)

        filename = (
            f"tts_{hashlib.md5(f'{tts_text[:40]}{time.time()}'.encode()).hexdigest()[:12]}"
            f"_{tts_lang}.{audio_format}"
        )
        with open(os.path.join(audio_dir, filename), "wb") as f:
            f.write(resp.content)

        return {
            "success": True,
            "audio_url": f"/static/audio/{filename}",
            "filename": filename,
            "language": tts_lang,
            "language_name": TTS_LANGUAGES.get(tts_lang, tts_lang),
            "speaker_id": speaker_id,
            "format": audio_format,
        }

    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"TTS API {e.response.status_code}: {e.response.text}",
            "audio_url": None
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "audio_url": None}


# ─── Info helpers ─────────────────────────────────────────────────────────────

def get_translation_languages() -> dict:
    return TRANSLATION_LANGUAGES

def get_tts_languages() -> dict:
    return TTS_LANGUAGES

def get_tts_speakers() -> list:
    return TTS_SPEAKERS

def get_supported_languages() -> dict:
    """Backwards-compatible alias."""
    return TRANSLATION_LANGUAGES
