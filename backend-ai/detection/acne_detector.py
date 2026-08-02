from ultralytics import YOLO

MODEL_PATH = "models/yolo/best.pt"


def load_yolo():
    print("Loading YOLO11 model...")

    model = YOLO(MODEL_PATH)

    print("YOLO loaded successfully!")

    return model