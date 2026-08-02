import cv2
import numpy as np


def calculate_brightness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return round(float(np.mean(gray)), 2)