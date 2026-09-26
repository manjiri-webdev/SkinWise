import cv2
import numpy as np

from fastapi import APIRouter, UploadFile, File, HTTPException

import config
from image_validation.pipeline import run_live_validation

router = APIRouter()


@router.post("/validate-live")
def validate_live(file: UploadFile = File(...)):
    if file.content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported."
        )

    file_bytes = file.file.read()
    nparr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to read image. The file may be corrupted or in an unsupported format."
        )

    return run_live_validation(image)