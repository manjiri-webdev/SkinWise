from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = str(BASE_DIR / "models" / "yolo" / "best.pt")


def load_yolo():
    print("Loading YOLO11 model...")

    model = YOLO(MODEL_PATH)

    print("YOLO loaded successfully!")

    return model