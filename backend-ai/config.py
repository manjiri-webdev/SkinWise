# Blur (Laplacian variance) - lenient for front-camera selfie filters and soft focus
BLUR_FAIL_THRESHOLD = 8
BLUR_WARNING_THRESHOLD = 20

# Brightness (mean grayscale intensity, 0-255) - relaxed to prevent false rejections
BRIGHTNESS_FAIL_LOW = 25
BRIGHTNESS_WARNING_LOW = 50
BRIGHTNESS_PASS_HIGH = 215
BRIGHTNESS_WARNING_HIGH = 245

# Face size (face bbox area / image area)
FACE_AREA_FAIL = 0.04
FACE_AREA_WARNING = 0.08

# Face position (normalized center must fall within this box)
FACE_POSITION_MIN = 0.15
FACE_POSITION_MAX = 0.85

# Face orientation (asymmetry between eye-to-nose distances)
ORIENTATION_PASS_THRESHOLD = 0.25
ORIENTATION_WARNING_THRESHOLD = 0.45

# Detection confidence (calibrated for diverse skin tones and lighting conditions)
MIN_FACE_DETECTION_CONFIDENCE = 0.50
YOLO_CONFIDENCE_THRESHOLD = 0.10

# Upload constraints
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024  # 8MB