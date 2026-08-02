import numpy as np
from PIL import Image

# Simple color map for 19 classes
COLORS = [
    (0, 0, 0),         # Background
    (255, 220, 177),   # Skin
    (255, 0, 0),       # Left Brow
    (200, 0, 0),       # Right Brow
    (0, 255, 0),       # Left Eye
    (0, 200, 0),       # Right Eye
    (0, 255, 255),     # Glasses
    (255, 255, 0),     # Left Ear
    (200, 200, 0),     # Right Ear
    (255, 0, 255),     # Earrings
    (0, 0, 255),       # Nose
    (255, 128, 0),     # Mouth
    (255, 100, 100),   # Upper Lip
    (255, 50, 50),     # Lower Lip
    (150, 75, 0),      # Neck
    (120, 120, 120),   # Necklace
    (80, 80, 80),      # Clothes
    (50, 50, 50),      # Hair
    (255, 255, 255)    # Hat
]

def save_mask(mask, output_path):

    color_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)

    for label, color in enumerate(COLORS):
        color_mask[mask == label] = color

    Image.fromarray(color_mask).save(output_path)