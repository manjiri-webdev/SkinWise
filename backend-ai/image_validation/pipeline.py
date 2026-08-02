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


def run_image_validation(image_path: str) -> Dict[str, Any]:
    image = load_image(image_path)

    if image is None:
        return {
            "ready_for_analysis": False,
            "error": "Unable to read image. The file may be corrupted or in an unsupported format.",
        }

    blur_result = validate_blur(image)
    brightness_result = validate_brightness(image)
    face_result = validate_face(image)
    orientation_result = validate_face_orientation(image)

    # Extract face data for single face validation
    from image_validation.face_detection import detect_faces
    face_data = detect_faces(image)
    single_face_result = validate_single_face(face_data)

    ready = (
        blur_result["status"] != "failed"
        and brightness_result["status"] != "failed"
        and face_result["status"] != "failed"
        and single_face_result["status"] != "failed"
        and orientation_result["status"] != "failed"
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