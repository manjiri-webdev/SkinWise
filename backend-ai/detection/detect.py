import config
from model_manager import yolo_model
from detection.utils import parse_yolo_results
import numpy as np

def detect_acne(image):
    conf_thresh = getattr(config, "YOLO_CONFIDENCE_THRESHOLD", 0.10)
    results = yolo_model.predict(
        source=image,
        conf=conf_thresh,
        imgsz=640,
        verbose=False
    )

    return parse_yolo_results(results)