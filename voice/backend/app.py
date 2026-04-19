import json
import os
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

app = FastAPI(title="Presentation Assistant Backend")

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_FILE = BASE_DIR / "transcripts.txt"
COMMANDS_FILE = BASE_DIR / "commands.txt"
TRANSCRIPTS_JSONL_FILE = BASE_DIR / "transcripts_detailed.jsonl"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# OPENAI_API_KEY = ''
OPENAI_AUDIO_MODEL = os.getenv("OPENAI_AUDIO_MODEL", "whisper-1")
APP_BACKEND_URL = os.getenv("PRESENTIFY_APP_BACKEND_URL", "http://127.0.0.1:8000")
TRANSCRIPTION_PROMPT = os.getenv(
    "TRANSCRIPTION_PROMPT",
    "This is a live presentation or lecture transcript. Keep punctuation clean. "
    "Preserve presentation commands such as next slide, previous slide, save board, "
    "start focus mode, stop focus mode when spoken.",
)

ALLOWED_COMMANDS = {
    "NEXT_SLIDE",
    "PREVIOUS_SLIDE",
    "SAVE_BOARD",
    "START_FOCUS_MODE",
    "STOP_FOCUS_MODE",
}

COMMAND_PATTERNS = {
    "NEXT_SLIDE": {
        "next slide",
        "go to the next slide",
        "move to the next slide",
        "slide forward",
        "advance slide",
    },
    "PREVIOUS_SLIDE": {
        "previous slide",
        "go to the previous slide",
        "go back",
        "go back a slide",
        "slide back",
        "back slide",
    },
    "SAVE_BOARD": {
        "save board",
        "capture board",
        "save whiteboard",
        "capture whiteboard",
    },
    "START_FOCUS_MODE": {
        "start focus mode",
        "focus mode on",
    },
    "STOP_FOCUS_MODE": {
        "stop focus mode",
        "focus mode off",
    },
}

class CommandRequest(BaseModel):
    command: str
    source: str
    rawText: str | None = None


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "message": "Presentation assistant backend is running.",
        "openai_model": OPENAI_AUDIO_MODEL,
        "openai_ready": bool(OPENAI_API_KEY and OpenAI is not None),
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "openai_ready": bool(OPENAI_API_KEY and OpenAI is not None),
        "model": OPENAI_AUDIO_MODEL,
    }


@app.post("/command")
async def handle_command(item: CommandRequest) -> dict[str, Any]:
    timestamp = now_str()

    if item.command not in ALLOWED_COMMANDS:
        return {
            "ok": False,
            "error": "Invalid command",
            "received": item.command,
            "timestamp": timestamp,
        }

    log_line = (
        f"[{timestamp}] command={item.command} "
        f"source={item.source} rawText={item.rawText}\n"
    )
    append_text(COMMANDS_FILE, log_line)

    action_result = run_command_action(item.command)
    return {
        "ok": True,
        "command": item.command,
        "source": item.source,
        "rawText": item.rawText,
        "action_result": action_result,
        "timestamp": timestamp,
    }


@app.post("/transcribe-chunk")
async def transcribe_chunk(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    language: str = Form("en"),
    pause_before_ms: int = Form(0),
    segment_started_at_ms: int = Form(0),
    segment_ended_at_ms: int = Form(0),
    speech_started_at_ms: int = Form(0),
    speech_ended_at_ms: int = Form(0),
    rms_avg: float = Form(0.0),
    speech_ratio: float = Form(0.0),
):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")
    if OpenAI is None:
        raise HTTPException(status_code=500, detail="openai package is not installed.")

    raw_audio = await audio.read()
    if not raw_audio:
        raise HTTPException(status_code=400, detail="Uploaded audio chunk is empty.")

    started = time.perf_counter()
    transcription = transcribe_with_whisper(raw_audio, audio.filename or f"chunk-{chunk_index}.webm", language)
    latency_ms = int((time.perf_counter() - started) * 1000)

    transcript_text = clean_text(transcription.get("text", ""))
    detected_command = map_transcript_to_command(transcript_text)

    payload = {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "chunk_index": chunk_index,
        "timestamp": now_str(),
        "language": language,
        "text": transcript_text,
        "detected_command": detected_command,
        "pause_before_ms": pause_before_ms,
        "segment_started_at_ms": segment_started_at_ms,
        "segment_ended_at_ms": segment_ended_at_ms,
        "speech_started_at_ms": speech_started_at_ms,
        "speech_ended_at_ms": speech_ended_at_ms,
        "segment_duration_ms": max(0, segment_ended_at_ms - segment_started_at_ms),
        "speech_duration_ms": max(0, speech_ended_at_ms - speech_started_at_ms),
        "rms_avg": round(rms_avg, 6),
        "speech_ratio": round(speech_ratio, 4),
        "latency_ms": latency_ms,
        "model": OPENAI_AUDIO_MODEL,
        "raw_response": transcription,
    }

    append_text(
        TRANSCRIPTS_FILE,
        f"[{payload['timestamp']}] {transcript_text} | pause_before_ms={pause_before_ms} | latency_ms={latency_ms}\n",
    )
    append_jsonl(TRANSCRIPTS_JSONL_FILE, payload)

    command_result = None
    if detected_command:
        command_result = run_command_action(detected_command)
        append_text(
            COMMANDS_FILE,
            f"[{payload['timestamp']}] command={detected_command} source=voice rawText={transcript_text}\n",
        )

    return {
        "ok": True,
        "session_id": session_id,
        "chunk_index": chunk_index,
        "text": transcript_text,
        "detected_command": detected_command,
        "command_result": command_result,
        "latency_ms": latency_ms,
        "pause_before_ms": pause_before_ms,
        "segment_duration_ms": payload["segment_duration_ms"],
        "speech_duration_ms": payload["speech_duration_ms"],
        "rms_avg": payload["rms_avg"],
        "speech_ratio": payload["speech_ratio"],
        "model": OPENAI_AUDIO_MODEL,
    }


def transcribe_with_whisper(audio_bytes: bytes, filename: str, language: str) -> dict[str, Any]:
    client = OpenAI(api_key=OPENAI_API_KEY)

    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name

    try:
        with open(temp_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=OPENAI_AUDIO_MODEL,
                file=f,
                language=language,
                prompt=TRANSCRIPTION_PROMPT,
                response_format="verbose_json",
                temperature=0,
            )

        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif isinstance(response, dict):
            data = response
        else:
            data = {"text": getattr(response, "text", str(response))}
        return data
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def append_text(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def normalize_text(text: str) -> str:
    return (
        (text or "")
        .lower()
        .strip()
        .replace("?", " ")
        .replace("!", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
    )


def map_transcript_to_command(text: str) -> str | None:
    normalized = " ".join(normalize_text(text).split())
    for command, phrases in COMMAND_PATTERNS.items():
        if normalized in phrases:
            return command
    return None


def run_command_action(command: str) -> str:
    action_map = {
        "NEXT_SLIDE": "next_slide",
        "PREVIOUS_SLIDE": "previous_slide",
        "SAVE_BOARD": "save_board",
        "START_FOCUS_MODE": "focus_start",
        "STOP_FOCUS_MODE": "focus_stop",
    }
    action = action_map.get(command)
    if not action:
        return "Unknown command"

    payload = json.dumps({"action": action, "source": "speech"}).encode("utf-8")
    req = request.Request(
        f"{APP_BACKEND_URL}/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=2.0) as response:
            body = response.read().decode("utf-8")
            return f"Forwarded to app backend: {body}"
    except error.HTTPError as exc:
        return f"App backend rejected command: {exc.read().decode('utf-8')}"
    except Exception as exc:  # pragma: no cover
        return f"Error executing command: {exc}"