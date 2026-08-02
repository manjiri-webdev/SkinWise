import os
import uuid
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

import config
from image_validation.pipeline import run_image_validation
from routes.validation import router as validation_router
from detection.detect import detect_acne
from analysis.acne_summary import summarize_acne
from analysis.severity import calculate_severity

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(validation_router)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class UploadResponse(BaseModel):
    filename: str
    ready_for_analysis: bool
    validation: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    severity: Optional[Dict[str, Any]] = None
    acne_detections: Optional[Any] = None


@app.get("/")
def home():
    return {"message": "Welcome to SkinWise AI Backend!"}

@app.post("/validate-live")
def validate_live(file: UploadFile = File(...)):
    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported."
        )

    extension = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    try:
        validation = run_image_validation(file_path)
        print(validation)
        
        return {
        "ready_for_analysis": validation["ready_for_analysis"],
        "validation": validation,
        }

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/upload", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...)):
    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    file_bytes = file.file.read()
    if len(file_bytes) > config.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds the 8MB size limit.")

    extension = os.path.splitext(file.filename)[1].lower()
    safe_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    try:
        validation = run_image_validation(file_path)

        if not validation["ready_for_analysis"]:
            return UploadResponse(
                filename=safe_filename,
                ready_for_analysis=False,
                validation=validation,
            )

        acne_detections = detect_acne(file_path)
        summary = summarize_acne(acne_detections)
        severity = calculate_severity(summary)

        return UploadResponse(
            filename=safe_filename,
            ready_for_analysis=True,
            validation=validation,
            summary=summary,
            severity=severity,
            acne_detections=acne_detections,
        )
    finally:
        pass