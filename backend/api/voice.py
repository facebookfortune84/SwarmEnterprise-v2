import os
import uuid
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from pathlib import Path

router = APIRouter(prefix="/api/voice", tags=["Voice"])
logger = logging.getLogger("VoiceAPI")

OUTPUT_DIR = Path(os.getenv('SWARM_OUTPUT_DIR', Path(__file__).resolve().parents[2] / 'output'))
AUDIO_DIR = OUTPUT_DIR / 'audio'
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class TTSRequest(BaseModel):
    text: str
    voice: str | None = "alloy"

@router.post('/tts')
async def tts(req: TTSRequest):
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail='ElevenLabs API key not configured')

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice}"
    headers = {
        'xi-api-key': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'text': req.text,
        'voice': req.voice
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        audio_bytes = r.content
        filename = AUDIO_DIR / f"tts_{uuid.uuid4().hex}.mp3"
        with open(filename, 'wb') as f:
            f.write(audio_bytes)
        return { 'url': f"/static/audio/{filename.name}", 'path': str(filename) }
    except Exception as e:
        logger.exception('TTS failed: %s', e)
        raise HTTPException(status_code=502, detail=str(e))
