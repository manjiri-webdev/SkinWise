import torch
from models.bisenet.model import BiSeNet

MODEL_PATH = "models/bisenet/79999_iter.pth"


def load_bisenet():

    model = BiSeNet(n_classes=19)

    state_dict = torch.load(
        MODEL_PATH,
        map_location="cpu"
    )

    model.load_state_dict(state_dict)

    model.eval()

    return model