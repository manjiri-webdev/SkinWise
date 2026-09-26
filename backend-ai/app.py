import os
import uuid
import cv2
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, Form
from pydantic import BaseModel

import config
import supabase_config
from auth_utils import get_current_user
from image_validation.pipeline import run_image_validation
from routes.validation import router as validation_router
from routes.personalization import router as personalization_router
from routes.history import router as history_router
from detection.detect import detect_acne
from analysis.acne_summary import summarize_acne
from analysis.severity import calculate_severity

import re
from starlette.types import ASGIApp, Scope, Receive, Send

cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url.strip() not in cors_origins:
    cors_origins.append(frontend_url.strip())
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    for origin in cors_origins_env.split(","):
        origin_clean = origin.strip()
        if origin_clean and origin_clean not in cors_origins:
            cors_origins.append(origin_clean)

class NormalizePathMiddleware:
    """
    Normalizes request paths by collapsing consecutive slashes (e.g. //personalization -> /personalization)
    so routing never returns 404 due to client-side trailing/duplicate slash variations.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            scope["path"] = re.sub(r"/+", "/", scope["path"])
            if "raw_path" in scope:
                scope["raw_path"] = re.sub(b"/+", b"/", scope["raw_path"])
        await self.app(scope, receive, send)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(NormalizePathMiddleware)
app.include_router(validation_router)
app.include_router(personalization_router)
app.include_router(history_router)

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



@app.post("/upload", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...), user_id: str = Depends(get_current_user), is_file_upload: bool = Form(False)):
    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    file_bytes = file.file.read()
    if len(file_bytes) > config.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds the 8MB size limit.")

    # Strictly in-memory image processing for privacy compliance (zero persistent image storage)
    nparr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image. Unsupported format or corrupt data.")

    validation = run_image_validation(image, skip_position_check=is_file_upload)

    if not validation["ready_for_analysis"]:
        return UploadResponse(
            filename=file.filename or "image.jpg",
            ready_for_analysis=False,
            validation=validation,
        )

    acne_detections = detect_acne(image)
    summary = summarize_acne(acne_detections)
    severity = calculate_severity(summary)

    # Persist analysis results to Supabase (numerical/structured metrics only; zero image persistence)
    try:
        analysis_record = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "model_name": "YOLO",
            "model_version": "v1",
            "blackheads": summary["blackheads"],
            "whiteheads": summary["whiteheads"],
            "papules": summary["papules"],
            "pustules": summary["pustules"],
            "nodules": summary["nodules"],
            "dark_spots": summary["dark_spots"],  # Already converted from "dark spot" in summarize_acne
            "total_lesions": summary["total_lesions"],
            "severity": severity["level"],
            "severity_score": severity["score"],
            "detections_json": acne_detections
        }
        
        supabase_config.supabase.table("skin_analyses").insert(analysis_record).execute()
    except Exception as db_error:
        print(f"Failed to persist analysis results: {str(db_error)}")
        # Continue without failing the upload if database insert fails

    return UploadResponse(
        filename=file.filename or "image.jpg",
        ready_for_analysis=True,
        validation=validation,
        summary=summary,
        severity=severity,
        acne_detections=acne_detections,
    )