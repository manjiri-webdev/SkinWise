import cv2
import numpy as np

# BiSeNet Face Parsing Classes
FACE_CLASSES = {
    "BACKGROUND": 0,
    "SKIN": 1,
    "LEFT_BROW": 2,
    "RIGHT_BROW": 3,
    "LEFT_EYE": 4,
    "RIGHT_EYE": 5,
    "GLASSES": 6,
    "LEFT_EAR": 7,
    "RIGHT_EAR": 8,
    "EARRING": 9,
    "NOSE": 10,
    "MOUTH": 11,
    "UPPER_LIP": 12,
    "LOWER_LIP": 13,
    "NECK": 14,
    "NECKLACE": 15,
    "CLOTHES": 16,
    "HAIR": 17,
    "HAT": 18
}

def extract_skin(original_image_path, mask, output_path):

    image = cv2.imread(original_image_path)

    if image is None:
        return None

    # Resize original image to match BiSeNet output
    image = cv2.resize(image, (512, 512))

    # Keep only Skin class (Class = 1)
    # Regions to keep for skin analysis
    KEEP_CLASSES = [
        FACE_CLASSES["SKIN"],
        FACE_CLASSES["NOSE"]
    ]

    skin_mask = np.isin(mask, KEEP_CLASSES).astype(np.uint8)
    
    # Convert mask into 3 channels
    skin_mask = np.stack([skin_mask] * 3, axis=-1)

    # Remove everything except skin
    skin_only = image * skin_mask

    cv2.imwrite(output_path, skin_only)

    return skin_only