from typing import Any, Dict, Optional
import numpy as np


def detect_face_orientation(face_data_or_image: Any) -> Dict[str, Any]:
    """
    Computes face orientation directly from the 6 facial keypoints extracted
    during MediaPipe face detection. Zero heavy FaceMesh model overhead.
    """
    if isinstance(face_data_or_image, dict) and "keypoints" in face_data_or_image:
        face_data = face_data_or_image
    elif isinstance(face_data_or_image, np.ndarray):
        from image_validation.face_detection import detect_faces
        face_data = detect_faces(face_data_or_image)
    else:
        return {"status": "passed", "face_orientation": "front", "message": "Face looking straight."}

    keypoints = face_data.get("keypoints", [])
    if len(keypoints) < 6 or not face_data.get("face_detected"):
        return {"status": "passed", "face_orientation": "front", "message": "Face looking straight."}

    # 0: RIGHT_EYE, 1: LEFT_EYE, 2: NOSE_TIP, 3: MOUTH_CENTER, 4: RIGHT_EAR, 5: LEFT_EAR
    right_eye = keypoints[0]
    left_eye = keypoints[1]
    nose = keypoints[2]
    mouth = keypoints[3]

    eye_span = abs(left_eye["x"] - right_eye["x"])
    dist_to_left = abs(nose["x"] - left_eye["x"])
    dist_to_right = abs(nose["x"] - right_eye["x"])
    yaw_asymmetry = abs(dist_to_left - dist_to_right) / eye_span if eye_span > 0.01 else 0.0

    avg_eye_y = (left_eye["y"] + right_eye["y"]) / 2.0
    vert_span = abs(mouth["y"] - avg_eye_y)
    expected_nose_y = avg_eye_y + 0.45 * vert_span
    pitch_offset = (nose["y"] - expected_nose_y) / vert_span if vert_span > 0.01 else 0.0

    # Non-blocking guidance warnings
    if yaw_asymmetry > 0.45:
        if dist_to_left > dist_to_right:
            return {"status": "warning", "face_orientation": "turned_left", "message": "Turn face slightly toward camera."}
        else:
            return {"status": "warning", "face_orientation": "turned_right", "message": "Turn face slightly toward camera."}

    if pitch_offset > 0.42:
        return {"status": "warning", "face_orientation": "looking_down", "message": "Look straight at the camera."}
    elif pitch_offset < -0.42:
        return {"status": "warning", "face_orientation": "looking_up", "message": "Look straight at the camera."}

    return {"status": "passed", "face_orientation": "front", "message": "Face is looking straight."}