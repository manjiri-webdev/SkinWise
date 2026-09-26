import cv2
import numpy as np
from typing import Optional, Union

def load_image(image_input: Union[str, np.ndarray, bytes, bytearray]) -> Optional[np.ndarray]:
    if isinstance(image_input, np.ndarray):
        return image_input

    if isinstance(image_input, (bytes, bytearray)):
        nparr = np.frombuffer(image_input, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if isinstance(image_input, str):
        return cv2.imread(image_input)

    return None


def get_image_info(image: np.ndarray):
    height, width, channels = image.shape

    return {
        "width": width,
        "height": height,
        "channels": channels
    }