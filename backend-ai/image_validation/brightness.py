from typing import Optional, Dict, Any
import cv2
import numpy as np


def calculate_brightness(image: np.ndarray, bbox: Optional[Dict[str, int]] = None) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if bbox:
        x1 = max(0, bbox.get("x1", 0))
        y1 = max(0, bbox.get("y1", 0))
        x2 = min(gray.shape[1], bbox.get("x2", gray.shape[1]))
        y2 = min(gray.shape[0], bbox.get("y2", gray.shape[0]))
        if (x2 - x1) > 20 and (y2 - y1) > 20:
            face_roi = gray[y1:y2, x1:x2]
            return round(float(np.mean(face_roi)), 2)
    return round(float(np.mean(gray)), 2)