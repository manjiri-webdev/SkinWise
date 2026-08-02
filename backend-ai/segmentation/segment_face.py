import torch
import torchvision.transforms as transforms

from PIL import Image

from model_manager import bisenet_model


transform = transforms.Compose([
    transforms.Resize((512, 512)),
    transforms.ToTensor(),
    transforms.Normalize(
        (0.485, 0.456, 0.406),
        (0.229, 0.224, 0.225)
    )
])


def segment_face(image_path):

    image = Image.open(image_path).convert("RGB")

    input_tensor = transform(image)

    input_tensor = input_tensor.unsqueeze(0)

    with torch.no_grad():

        output = bisenet_model(input_tensor)[0]

    parsing = output.squeeze(0).argmax(0)

    return parsing.numpy()