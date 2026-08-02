import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

import config
from image_validation.pipeline import run_image_validation

router = APIRouter()

TEMP_FOLDER = "uploads"
os.makedirs(TEMP_FOLDER, exist_ok=True)


@router.post("/validate-live")
def validate_live(file: UploadFile = File(...)):

    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported."
        )

    extension = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(TEMP_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    try:
        validation = run_image_validation(file_path)

        return validation
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)