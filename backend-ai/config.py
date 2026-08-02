# Blur (Laplacian variance) - temporarily lowered for laptop webcam testing
# Production values: BLUR_FAIL_THRESHOLD = 80, BLUR_WARNING_THRESHOLD = 150
BLUR_FAIL_THRESHOLD = 30
BLUR_WARNING_THRESHOLD = 60

# Brightness (mean grayscale intensity, 0-255) - relaxed for normal indoor lighting
BRIGHTNESS_FAIL_LOW = 40
BRIGHTNESS_WARNING_LOW = 70
BRIGHTNESS_PASS_HIGH = 200
BRIGHTNESS_WARNING_HIGH = 230

# Face size (face bbox area / image area)
FACE_AREA_FAIL = 0.06
FACE_AREA_WARNING = 0.12

# Face position (normalized center must fall within this box)
FACE_POSITION_MIN = 0.30
FACE_POSITION_MAX = 0.70

# Face orientation (asymmetry between eye-to-nose distances)
ORIENTATION_PASS_THRESHOLD = 0.03
ORIENTATION_WARNING_THRESHOLD = 0.06

# Detection confidence
MIN_FACE_DETECTION_CONFIDENCE = 0.8

# Upload constraints
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024  # 8MB