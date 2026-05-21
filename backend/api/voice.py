"""
Text-to-speech (TTS) API endpoints.

This module provides an endpoint for generating speech audio using the
ElevenLabs API. Audio files are stored in the project's output directory.
"""

import logging
import os
import uuid
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/voice", tags=["Voice"])
logger = logging.getLogger("VoiceAPI")

# Resolve output directory for audio files
OUTPUT_DIR = Path(
    os.getenv(
        "SWARM_OUTPUT_DIR",
        Path(__file__).resolve().parents[2] / "output",
    )
)
AUDIO_DIR = OUTPUT_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class TTSRequest(BaseModel):
    """Payload for generating text-to-speech audio."""

    text: str
    voice: str | None = "alloy"


@router.post("/tts")
async def tts(request: TTSRequest):
    """
    Generate speech audio using the ElevenLabs API.

    Args:
        request (TTSRequest): Text and voice selection.

    Raises:
        HTTPException: If API key is missing or request fails.

    Returns:
        dict: URL and filesystem path of generated audio file.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key not configured",
        )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{request.voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": request.text,
        "voice": request.voice,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        audio_bytes = response.content
        filename = AUDIO_DIR / f"tts_{uuid.uuid4().hex}.mp3"

        with open(filename, "wb") as audio_file:
            audio_file.write(audio_bytes)

        return {
            "url": f"/static/audio/{filename.name}",
            "path": str(filename),
        }

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("TTS failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
