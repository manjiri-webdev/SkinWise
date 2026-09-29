from typing import Any, Dict

from utils.image_reader import load_image
from image_validation.face_detection import detect_faces
from image_validation.validator import (
    validate_blur,
    validate_brightness,
    validate_face,
    validate_face_orientation,
    validate_single_face,
)


def run_image_validation(image_input: Any, skip_position_check: bool = False) -> Dict[str, Any]:
    image = load_image(image_input)

    if image is None:
        return {
            "ready_for_analysis": False,
            "error": "Unable to read image. The file may be corrupted or in an unsupported format.",
        }

    # 1. Single Face Detection pass (returns bbox + keypoints in ~20ms)
    face_data = detect_faces(image)
    face_result = validate_face(image, face_data=face_data)
    single_face_result = validate_single_face(face_data)

    # 2. Lighting check evaluated on face ROI
    brightness_result = validate_brightness(image, face_data=face_data)

    # 3. Blur check (lenient so soft focus / smoothed selfies pass)
    blur_result = validate_blur(image)

    # 4. Instant orientation evaluation from keypoints (guidance only)
    orientation_result = validate_face_orientation(face_data)

    # Analysis is ready when a single face is confirmed and lighting/blur are usable
    ready = (
        face_result["status"] != "failed"
        and single_face_result["status"] != "failed"
        and brightness_result["status"] != "failed"
        and blur_result["status"] != "failed"
    )

    return {
        "ready_for_analysis": ready,
        "validation": {
            "blur": blur_result,
            "brightness": brightness_result,
            "face_detection": face_result,
            "single_face": single_face_result,
            "face_orientation": orientation_result,
        },
    }


def run_live_validation(image_input: Any) -> Dict[str, Any]:
    """Live validation without blur check and face position as guidance only."""
    image = load_image(image_input)

    if image is None:
        return {
            "ready_for_analysis": False,
            "error": "Unable to read image. The file may be corrupted or in an unsupported format.",
        }

    # 1. Single Face Detection pass (~20ms)
    face_data = detect_faces(image)
    face_result = validate_face(image, face_data=face_data)
    single_face_result = validate_single_face(face_data)

    # 2. Lighting check evaluated on face ROI
    brightness_result = validate_brightness(image, face_data=face_data)

    # 3. Instant orientation evaluation from keypoints
    orientation_result = validate_face_orientation(face_data)

    ready = (
        face_result["status"] != "failed"
        and single_face_result["status"] != "failed"
        and brightness_result["status"] != "failed"
    )

    guidance = "Keep your face centered in the frame."
    if orientation_result.get("status") == "warning":
        guidance = orientation_result.get("message", guidance)

    return {
        "ready_for_analysis": ready,
        "validation": {
            "brightness": brightness_result,
            "face_detection": face_result,
            "single_face": single_face_result,
            "face_orientation": orientation_result,
        },
        "guidance": guidance
    }