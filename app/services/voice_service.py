"""Voice Interview & Whisper Speech-to-Text Service.

Handles:
- Audio file upload and processing
- Speech-to-text transcription (OpenAI Whisper API or local whisper)
- Voice interview session management
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.services.llm_service import llm_service


class WhisperService:
    """Speech-to-text service using OpenAI Whisper API."""

    def __init__(self):
        self.supported_formats = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}
        self.max_file_size_mb = 25  # Whisper API limit

    @property
    def is_available(self) -> bool:
        """Check if Whisper API is available (requires OpenAI API key)."""
        return llm_service.is_available

    def transcribe_audio(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio file to text using OpenAI Whisper API.
        
        Args:
            file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
        
        Returns:
            dict with transcript, language, duration
        """
        if not self.is_available:
            return self._fallback_transcription(file_path)

        # Validate file
        ext = Path(file_path).suffix.lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {ext}. Supported: {self.supported_formats}")

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(f"File too large ({file_size_mb:.1f}MB). Max: {self.max_file_size_mb}MB")

        try:
            with open(file_path, "rb") as audio_file:
                kwargs = {"model": "whisper-1", "file": audio_file, "response_format": "verbose_json"}
                if language:
                    kwargs["language"] = language

                response = llm_service.client.audio.transcriptions.create(**kwargs)

            return {
                "transcript": response.text,
                "language": getattr(response, "language", language or "en"),
                "duration_seconds": getattr(response, "duration", None),
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                    }
                    for seg in getattr(response, "segments", [])
                ],
                "status": "transcribed",
            }
        except Exception as e:
            return {
                "transcript": "",
                "language": language or "unknown",
                "duration_seconds": None,
                "segments": [],
                "status": "error",
                "error": str(e),
            }

    def _fallback_transcription(self, file_path: str) -> dict:
        """Fallback when Whisper API is not available."""
        return {
            "transcript": "",
            "language": "en",
            "duration_seconds": None,
            "segments": [],
            "status": "unavailable",
            "error": "Whisper API not configured. Set OPENAI_API_KEY in .env",
        }

    def process_voice_response(
        self,
        audio_path: str,
        question_id: int,
        language: Optional[str] = None,
    ) -> dict:
        """Process a single voice response for an interview question."""
        result = self.transcribe_audio(audio_path, language)
        return {
            "question_id": question_id,
            "audio_path": audio_path,
            "transcript": result["transcript"],
            "language": result["language"],
            "duration_seconds": result["duration_seconds"],
            "status": result["status"],
        }


class VoiceInterviewManager:
    """Manages voice interview sessions."""

    def __init__(self):
        self.whisper = WhisperService()
        self.upload_dir = Path(settings.UPLOAD_DIR).parent / "audio"

    def create_session(self, interview_id: int) -> dict:
        """Create a voice interview session."""
        session_dir = self.upload_dir / str(interview_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        return {
            "interview_id": interview_id,
            "session_dir": str(session_dir),
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_audio(self, interview_id: int, question_id: int, audio_content: bytes, filename: str) -> str:
        """Save an audio response file."""
        session_dir = self.upload_dir / str(interview_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix.lower() or ".webm"
        file_path = session_dir / f"q{question_id}{ext}"

        with open(file_path, "wb") as f:
            f.write(audio_content)

        return str(file_path)

    def transcribe_all_responses(self, interview_id: int, audio_paths: list[dict]) -> list[dict]:
        """Transcribe all audio responses for an interview."""
        transcripts = []
        for item in audio_paths:
            result = self.whisper.process_voice_response(
                audio_path=item["path"],
                question_id=item["question_id"],
            )
            transcripts.append(result)
        return transcripts


# Singletons
whisper_service = WhisperService()
voice_interview_manager = VoiceInterviewManager()
