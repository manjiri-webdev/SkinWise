import cv2

from detection.detect import detect_acne

image = cv2.imread("uploads/acne.jpg")

predictions = detect_acne(image)

print(predictions)
