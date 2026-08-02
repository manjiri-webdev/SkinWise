from model_manager import yolo_model
from detection.utils import parse_yolo_results
import numpy as np

def detect_acne(image):
    # if isinstance(image, np.ndarray):
    #     print("Shape:", image.shape)
    #     print("dtype:", image.dtype)
    # else:
    #     print("Value:", image)

    # print("=" * 60)

    results = yolo_model.predict(
        source=image,
        conf=0.10,
        verbose=True
    )

    return parse_yolo_results(results)