import cv2
import numpy as np
from typing import Optional

def load_image(image_path: str) -> Optional[np.ndarray]:
    image = cv2.imread(image_path)

    if image is None:
        return None

    return image


def get_image_info(image: np.ndarray):
    height, width, channels = image.shape

    return {
        "width": width,
        "height": height,
        "channels": channels
    }