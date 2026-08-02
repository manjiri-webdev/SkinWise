from typing import Any, Dict, Optional

import cv2
import mediapipe as mp
import numpy as np

from config import MIN_FACE_DETECTION_CONFIDENCE

_mp_face_detection = mp.solutions.face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=MIN_FACE_DETECTION_CONFIDENCE,
)

def detect_faces(image: np.ndarray) -> Optional[Dict[str, Any]]:
    image_height, image_width = image.shape[:2]
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = _mp_face_detection.process(rgb_image)

    if not results.detections:
        return {
            "face_detected": False,
            "face_count": 0
        }

    detection = results.detections[0]
    rel_box = detection.location_data.relative_bounding_box

    x1 = int(rel_box.xmin * image_width)
    y1 = int(rel_box.ymin * image_height)
    width = int(rel_box.width * image_width)
    height = int(rel_box.height * image_height)

    return {
        "face_detected": True,
        "face_count": len(results.detections),
        "bounding_box": {
            "x1": x1,
            "y1": y1,
            "x2": x1 + width,
            "y2": y1 + height,
            "width": width,
            "height": height,
        },
        "confidence": round(float(detection.score[0]), 3),
        "image_width": image_width,
        "image_height": image_height,
    }