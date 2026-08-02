from segmentation.bisenet_loader import load_bisenet
from detection.acne_detector import load_yolo

print("Loading BiSeNet...")
bisenet_model = load_bisenet()

print("BiSeNet loaded successfully!")

print("Loading YOLO...")
yolo_model = load_yolo()

print("YOLO loaded successfully!")