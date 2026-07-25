import cv2

def read_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return None

    height, width, channels = image.shape

    return{
        "width": width,
        "height": height,
        "channels": channels
    }