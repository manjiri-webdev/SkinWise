import cv2
import numpy as np

def calculate_brightness(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness_score = np.mean(gray)

    return round(float(brightness_score), 2)