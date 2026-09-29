# Blur (Laplacian variance) - calibrated for mobile cameras and smooth selfie filters
BLUR_FAIL_THRESHOLD = 15
BLUR_WARNING_THRESHOLD = 30

# Brightness (mean grayscale intensity, 0-255) - relaxed for normal indoor lighting
BRIGHTNESS_FAIL_LOW = 40
BRIGHTNESS_WARNING_LOW = 70
BRIGHTNESS_PASS_HIGH = 200
BRIGHTNESS_WARNING_HIGH = 230

# Face size (face bbox area / image area)
FACE_AREA_FAIL = 0.06
FACE_AREA_WARNING = 0.12

# Face position (normalized center must fall within this box)
FACE_POSITION_MIN = 0.20
FACE_POSITION_MAX = 0.80

# Face orientation (asymmetry between eye-to-nose distances)
ORIENTATION_PASS_THRESHOLD = 0.06
ORIENTATION_WARNING_THRESHOLD = 0.12

# Detection confidence (calibrated for diverse skin tones and lighting conditions)
MIN_FACE_DETECTION_CONFIDENCE = 0.55
YOLO_CONFIDENCE_THRESHOLD = 0.10

# Upload constraints
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024  # 8MB