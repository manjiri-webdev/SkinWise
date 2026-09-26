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

    blur_result = validate_blur(image)
    brightness_result = validate_brightness(image)
    face_result = validate_face(image)
    orientation_result = validate_face_orientation(image)

    print(f"DEBUG run_image_validation: blur_result={blur_result}")
    print(f"DEBUG run_image_validation: brightness_result={brightness_result}")
    print(f"DEBUG run_image_validation: face_result={face_result}")
    print(f"DEBUG run_image_validation: orientation_result={orientation_result}")
    print(f"DEBUG run_image_validation: skip_position_check={skip_position_check}")

    # Extract face data for single face validation
    from image_validation.face_detection import detect_faces
    face_data = detect_faces(image)
    single_face_result = validate_single_face(face_data)

    print(f"DEBUG run_image_validation: single_face_result={single_face_result}")

    # For uploaded photos, skip face orientation check (which includes position/centering aspects)
    if skip_position_check:
        ready = (
            blur_result["status"] != "failed"
            and brightness_result["status"] != "failed"
            and face_result["status"] != "failed"
            and single_face_result["status"] != "failed"
        )
    else:
        ready = (
            blur_result["status"] != "failed"
            and brightness_result["status"] != "failed"
            and face_result["status"] != "failed"
            and single_face_result["status"] != "failed"
            and orientation_result["status"] != "failed"
        )

    print(f"DEBUG run_image_validation: ready={ready}")

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

    brightness_result = validate_brightness(image)
    face_result = validate_face(image)
    orientation_result = validate_face_orientation(image)

    # Extract face data from validate_face result to avoid duplicate detection
    face_data = face_result.get("face_data") if isinstance(face_result, dict) and "face_data" in face_result else None
    if face_data:
        single_face_result = validate_single_face(face_data)
    else:
        # Fallback: run detection if face_data not available
        from image_validation.face_detection import detect_faces
        face_data = detect_faces(image)
        single_face_result = validate_single_face(face_data)

    ready = (
        brightness_result["status"] != "failed"
        and face_result["status"] != "failed"
        and single_face_result["status"] != "failed"
        and orientation_result["status"] != "failed"
    )

    return {
        "ready_for_analysis": ready,
        "validation": {
            "brightness": brightness_result,
            "face_detection": face_result,
            "single_face": single_face_result,
            "face_orientation": orientation_result,
        },
        "guidance": "Keep your face centered in the frame."
    }