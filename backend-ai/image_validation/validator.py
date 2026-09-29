from typing import Any, Dict, Optional

import config
from image_validation.blur import calculate_blur
from image_validation.brightness import calculate_brightness
from image_validation.face_detection import detect_faces
from image_validation.face_orientation import detect_face_orientation


def validate_blur(image) -> Dict[str, Any]:
    blur_score = calculate_blur(image)

    if blur_score < config.BLUR_FAIL_THRESHOLD:
        return {"status": "failed", "message": "Image is too blurry. Please hold steady and improve focus.", "blur_score": blur_score}
    if blur_score < config.BLUR_WARNING_THRESHOLD:
        return {"status": "warning", "message": "Image is slightly soft. Results may be less accurate.", "blur_score": blur_score}
    return {"status": "passed", "message": "Image quality is clear.", "blur_score": blur_score}


def validate_brightness(image, face_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    bbox = face_data.get("bounding_box") if face_data else None
    brightness_score = calculate_brightness(image, bbox=bbox)

    if brightness_score < config.BRIGHTNESS_FAIL_LOW:
        return {"status": "failed", "message": "Lighting is too dark to analyze. Please move to a brighter area.", "brightness_score": brightness_score}
    if brightness_score < config.BRIGHTNESS_WARNING_LOW:
        return {"status": "warning", "message": "Lighting is slightly dark. Hold steady in even light.", "brightness_score": brightness_score}
    if brightness_score <= config.BRIGHTNESS_PASS_HIGH:
        return {"status": "passed", "message": "Brightness is suitable for analysis.", "brightness_score": brightness_score}
    if brightness_score <= config.BRIGHTNESS_WARNING_HIGH:
        return {"status": "warning", "message": "Lighting is slightly bright. Results are best without harsh glare.", "brightness_score": brightness_score}
    return {"status": "failed", "message": "Image is overexposed. Please reduce the lighting or glare.", "brightness_score": brightness_score}


def validate_face_size(face_data: Dict[str, Any]) -> Dict[str, Any]:
    bbox = face_data["bounding_box"]
    face_area = (bbox["width"] * bbox["height"]) / (face_data["image_width"] * face_data["image_height"])

    if face_area < config.FACE_AREA_FAIL:
        return {"status": "failed", "face_size": "small", "message": "Move closer to the camera."}
    if face_area < config.FACE_AREA_WARNING:
        return {"status": "warning", "face_size": "medium", "message": "Face is slightly small. Results may be less accurate."}
    return {"status": "passed", "face_size": "good", "message": "Face size is suitable."}


def validate_face_position(face_data: Dict[str, Any]) -> Dict[str, Any]:
    bbox = face_data["bounding_box"]
    center_x = ((bbox["x1"] + bbox["x2"]) / 2) / face_data["image_width"]
    center_y = ((bbox["y1"] + bbox["y2"]) / 2) / face_data["image_height"]

    # More lenient face position threshold (30%-70% → 20%-80%)
    position_min = 0.20
    position_max = 0.80

    if not (position_min <= center_x <= position_max and
            position_min <= center_y <= position_max):
        return {"status": "failed", "face_position": "off_center", "message": "Please center your face in the camera."}

    return {"status": "passed", "face_position": "center", "message": "Face is well centered."}


def validate_face(image, face_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if face_data is None:
        face_data = detect_faces(image)

    if not face_data["face_detected"]:
        return {"status": "failed", "message": "No face detected. Please ensure your face is visible in the camera.", "face_data": face_data}

    if face_data["face_count"] > 1:
        return {"status": "failed", "message": "Multiple faces detected. Please ensure only one person is visible.", "face_data": face_data}

    # Check detection confidence
    if face_data["confidence"] < config.MIN_FACE_DETECTION_CONFIDENCE:
        return {"status": "failed", "message": "Face detection confidence is too low. Please move closer to the camera or improve lighting.", "face_data": face_data}

    # Check face size
    size_validation = validate_face_size(face_data)
    if size_validation["status"] == "failed":
        return {"status": "failed", "message": size_validation["message"], "face_data": face_data}

    return {
        "status": "passed",
        "message": "Face detected successfully.",
        "face_count": face_data["face_count"],
        "face_size": size_validation,
        "confidence": face_data["confidence"],
        "face_data": face_data,  # Include face_data to avoid duplicate detection
    }


def validate_single_face(face_data: Dict[str, Any]) -> Dict[str, Any]:
    if not face_data["face_detected"]:
        return {"status": "failed", "message": "No face detected. Please ensure your face is visible in the camera."}

    if face_data["face_count"] > 1:
        return {"status": "failed", "message": "Multiple faces detected. Please ensure only one person is visible."}

    return {"status": "passed", "message": "Single face confirmed."}


def validate_face_orientation(face_data_or_image: Any) -> Dict[str, Any]:
    return detect_face_orientation(face_data_or_image)