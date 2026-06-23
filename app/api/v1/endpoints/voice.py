"""Voice Interview endpoints - audio upload, transcription, voice-based interviews."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.interview import Interview, InterviewType, InterviewStatus
from app.models.job import JobApplication
from app.models.candidate import Candidate
from app.services.voice_service import voice_interview_manager, whisper_service

router = APIRouter(prefix="/voice", tags=["Voice Interview"])

ALLOWED_AUDIO_FORMATS = {".mp3", ".wav", ".webm", ".ogg", ".m4a", ".mp4"}


@router.post("/create-session")
def create_voice_session(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a voice interview session."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Update interview type to voice
    interview.interview_type = InterviewType.VOICE
    interview.status = InterviewStatus.IN_PROGRESS
    db.commit()

    session = voice_interview_manager.create_session(interview_id)
    return session


@router.post("/upload-response")
async def upload_voice_response(
    interview_id: int = Form(...),
    question_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an audio response for a specific interview question."""
    # Validate format
    ext = Path(audio.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {ALLOWED_AUDIO_FORMATS}",
        )

    # Validate interview exists
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Save audio
    content = await audio.read()
    file_path = voice_interview_manager.save_audio(
        interview_id=interview_id,
        question_id=question_id,
        audio_content=content,
        filename=audio.filename,
    )

    return {
        "status": "uploaded",
        "interview_id": interview_id,
        "question_id": question_id,
        "file_path": file_path,
        "file_size_bytes": len(content),
    }


@router.post("/transcribe/{interview_id}")
def transcribe_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Transcribe all audio responses for an interview using Whisper.
    Converts speech to text for AI evaluation.
    """
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Find audio files for this interview
    audio_dir = Path("uploads/audio") / str(interview_id)
    if not audio_dir.exists():
        raise HTTPException(status_code=404, detail="No audio files found")

    audio_files = []
    for f in sorted(audio_dir.iterdir()):
        if f.suffix.lower() in ALLOWED_AUDIO_FORMATS:
            # Extract question_id from filename (e.g., q1.webm)
            try:
                qid = int(f.stem.replace("q", ""))
            except ValueError:
                qid = 0
            audio_files.append({"path": str(f), "question_id": qid})

    if not audio_files:
        raise HTTPException(status_code=404, detail="No audio files to transcribe")

    # Transcribe
    transcripts = voice_interview_manager.transcribe_all_responses(interview_id, audio_files)

    # Update interview with transcript
    full_transcript = "\n\n".join(
        f"Q{t['question_id']}: {t['transcript']}" for t in transcripts if t["transcript"]
    )
    interview.transcript = full_transcript

    # Also format as responses for evaluation
    responses = [
        {"question_id": t["question_id"], "response": t["transcript"]}
        for t in transcripts
        if t["transcript"]
    ]
    interview.responses = responses
    interview.status = InterviewStatus.COMPLETED
    db.commit()

    return {
        "interview_id": interview_id,
        "transcripts": transcripts,
        "total_transcribed": len([t for t in transcripts if t["status"] == "transcribed"]),
        "whisper_available": whisper_service.is_available,
    }


@router.get("/status")
def get_voice_service_status(
    current_user: User = Depends(get_current_user),
):
    """Check voice interview service availability."""
    return {
        "whisper_available": whisper_service.is_available,
        "supported_formats": list(ALLOWED_AUDIO_FORMATS),
        "max_file_size_mb": whisper_service.max_file_size_mb,
    }
