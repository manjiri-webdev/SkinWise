import cv2
from detection.detect import detect_acne

image_path = "uploads/acne.jpg"

# Read image
image = cv2.imread(image_path)

# Detect acne
detections = detect_acne(image)

# Draw detections
for det in detections:
    x1, y1, x2, y2 = map(int, det["bbox"])

    label = f'{det["class_name"]} {det["confidence"]:.2f}'

    # Green rectangle
    cv2.rectangle(image, (x1, y1), (x2, y2), (0,255,0), 2)

    # Text
    cv2.putText(
        image,
        label,
        (x1, y1-8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0,255,0),
        2
    )

cv2.imwrite("prediction.jpg", image)

print("Prediction saved as prediction.jpg")