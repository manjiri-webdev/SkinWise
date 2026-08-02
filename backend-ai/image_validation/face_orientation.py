from typing import Any, Dict, Optional

import cv2
import mediapipe as mp
import numpy as np

# Load FaceMesh once when the application starts
_mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
)

def detect_face_orientation(image: np.ndarray) -> Optional[Dict[str, Any]]:
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = _mp_face_mesh.process(rgb_image)

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0]

    return {
        "nose": landmarks.landmark[1],
        "left_eye": landmarks.landmark[33],
        "right_eye": landmarks.landmark[263],
        "left_ear": landmarks.landmark[234],
        "right_ear": landmarks.landmark[454],
        "top_head": landmarks.landmark[10],
        "chin": landmarks.landmark[152],
    }