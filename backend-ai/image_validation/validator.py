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
        return {"status": "warning", "message": "Image is slightly blurry. Results may be less accurate.", "blur_score": blur_score}
    return {"status": "passed", "message": "Image quality is good.", "blur_score": blur_score}


def validate_brightness(image) -> Dict[str, Any]:
    brightness_score = calculate_brightness(image)

    if brightness_score < config.BRIGHTNESS_FAIL_LOW:
        return {"status": "failed", "message": "Image is too dark. Please move to a brighter area.", "brightness_score": brightness_score}
    if brightness_score < config.BRIGHTNESS_WARNING_LOW:
        return {"status": "warning", "message": "Image is slightly dark. Results may be less accurate.", "brightness_score": brightness_score}
    if brightness_score <= config.BRIGHTNESS_PASS_HIGH:
        return {"status": "passed", "message": "Brightness is suitable for analysis.", "brightness_score": brightness_score}
    if brightness_score <= config.BRIGHTNESS_WARNING_HIGH:
        return {"status": "warning", "message": "Image is slightly overexposed. Results may be less accurate.", "brightness_score": brightness_score}
    return {"status": "failed", "message": "Image is overexposed. Please reduce the lighting.", "brightness_score": brightness_score}


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

    if not (config.FACE_POSITION_MIN <= center_x <= config.FACE_POSITION_MAX and
            config.FACE_POSITION_MIN <= center_y <= config.FACE_POSITION_MAX):
        return {"status": "failed", "face_position": "off_center", "message": "Please center your face in the camera."}

    return {"status": "passed", "face_position": "center", "message": "Face is well centered."}


def validate_face(image) -> Dict[str, Any]:
    face_data = detect_faces(image)

    if not face_data["face_detected"]:
        return {"status": "failed", "message": "No face detected. Please ensure your face is visible in the camera."}

    if face_data["face_count"] > 1:
        return {"status": "failed", "message": "Multiple faces detected. Please ensure only one person is visible."}

    # Check detection confidence
    if face_data["confidence"] < config.MIN_FACE_DETECTION_CONFIDENCE:
        return {"status": "failed", "message": "Face detection confidence is too low. Please move closer to the camera or improve lighting."}

    # Check face size
    size_validation = validate_face_size(face_data)
    if size_validation["status"] == "failed":
        return {"status": "failed", "message": size_validation["message"]}

    # Check face position
    position_validation = validate_face_position(face_data)
    if position_validation["status"] == "warning":
        return {"status": "failed", "message": position_validation["message"]}

    return {
        "status": "passed",
        "message": "Face detected successfully.",
        "face_count": face_data["face_count"],
        "face_size": size_validation,
        "face_position": position_validation,
        "confidence": face_data["confidence"],
    }


def validate_single_face(face_data: Dict[str, Any]) -> Dict[str, Any]:
    if not face_data["face_detected"]:
        return {"status": "failed", "message": "No face detected. Please ensure your face is visible in the camera."}

    if face_data["face_count"] > 1:
        return {"status": "failed", "message": "Multiple faces detected. Please ensure only one person is visible."}

    return {"status": "passed", "message": "Single face confirmed."}


def validate_face_orientation(image) -> Dict[str, Any]:
    face_points = detect_face_orientation(image)

    if face_points is None:
        return {"status": "failed", "face_orientation": "unknown", "message": "Unable to determine face orientation."}

    nose = face_points["nose"]
    left_eye = face_points["left_eye"]
    right_eye = face_points["right_eye"]
    left_ear = face_points["left_ear"]
    right_ear = face_points["right_ear"]
    top_head = face_points["top_head"]
    chin = face_points["chin"]

    # Check left/right tilt (yaw) using eye-nose asymmetry
    left_distance = abs(nose.x - left_eye.x)
    right_distance = abs(right_eye.x - nose.x)
    yaw_difference = abs(left_distance - right_distance)

    # Check up/down tilt (pitch) using head landmarks
    vertical_center = (top_head.y + chin.y) / 2
    nose_y_offset = abs(nose.y - vertical_center)

    # Check ear visibility for left/right turn detection
    ear_width = abs(right_ear.x - left_ear.x)
    nose_to_left_ear = abs(nose.x - left_ear.x)
    nose_to_right_ear = abs(nose.x - right_ear.x)
    ear_asymmetry = abs(nose_to_left_ear - nose_to_right_ear) / ear_width if ear_width > 0 else 0

    # Determine orientation issues
    if yaw_difference > config.ORIENTATION_WARNING_THRESHOLD:
        if left_distance > right_distance:
            return {"status": "failed", "face_orientation": "turned_left", "message": "Turn your face slightly right."}
        else:
            return {"status": "failed", "face_orientation": "turned_right", "message": "Turn your face slightly left."}

    if ear_asymmetry > config.ORIENTATION_WARNING_THRESHOLD:
        if nose_to_left_ear > nose_to_right_ear:
            return {"status": "failed", "face_orientation": "turned_left", "message": "Turn your face slightly right."}
        else:
            return {"status": "failed", "face_orientation": "turned_right", "message": "Turn your face slightly left."}

    if nose_y_offset > config.ORIENTATION_WARNING_THRESHOLD:
        if nose.y < vertical_center:
            return {"status": "failed", "face_orientation": "looking_up", "message": "Look straight at the camera."}
        else:
            return {"status": "failed", "face_orientation": "looking_down", "message": "Look straight at the camera."}

    if yaw_difference > config.ORIENTATION_PASS_THRESHOLD:
        return {"status": "warning", "face_orientation": "slightly_turned", "message": "Please look directly at the camera."}

    return {"status": "passed", "face_orientation": "front", "message": "Face is looking straight."}