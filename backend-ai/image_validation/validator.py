from image_validation.blur import calculate_blur
from image_validation.brightness import calculate_brightness
from image_validation.face_detection import detect_faces

def validate_blur(image_path):

    blur_score = calculate_blur(image_path)

    if blur_score is None:
        return {
            "status": "failed",
            "message": "Unable to read image.",
            "blur_score": None
        }

    if blur_score < 80:
        return {
            "status": "failed",
            "message": "Image is too blurry. Please retake the image in better focus.",
            "blur_score": blur_score
        }

    elif blur_score < 150:
        return {
            "status": "warning",
            "message": "Image is slightly blurry. Results may be less accurate.",
            "blur_score": blur_score
        }

    else:
        return {
            "status": "accepted",
            "message": "Image quality is good.",
            "blur_score": blur_score
        }

def validate_brightness(image_path):

    brightness_score = calculate_brightness(image_path)

    if brightness_score is None:
        return {
            "status": "failed",
            "message": "Unable to read image.",
            "brightness_score": None
        }

    if brightness_score < 60:
        return {
            "status": "failed",
            "message": "Image is too dark. Please move to a brighter area.",
            "brightness_score": brightness_score
        }

    elif brightness_score < 100:
        return {
            "status": "warning",
            "message": "Image is slightly dark. Results may be less accurate.",
            "brightness_score": brightness_score
        }

    elif brightness_score <= 190:
        return {
            "status": "passed",
            "message": "Brightness is suitable for analysis.",
            "brightness_score": brightness_score
        }

    elif brightness_score <= 220:
        return {
            "status": "warning",
            "message": "Image is slightly overexposed. Results may be less accurate.",
            "brightness_score": brightness_score
        }

    else:
        return {
            "status": "failed",
            "message": "Image is overexposed. Please reduce the lighting.",
            "brightness_score": brightness_score
        }


def validate_face(image_path):

    result = detect_faces(image_path)

    if result is None:
        return {
            "status": "failed",
            "message": "Unable to read image."
        }

    if not result["face_detected"]:
        return {
            "status": "failed",
            "message": "No face detected. Please upload a clear facial image."
        }

    if result["face_count"] > 1:
        return {
            "status": "failed",
            "message": "Multiple faces detected. Please upload an image with only one person."
        }

    return {
        "status": "passed",
        "message": "Face detected successfully.",
        "face_count": result["face_count"]
    }