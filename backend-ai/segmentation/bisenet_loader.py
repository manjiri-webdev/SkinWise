import os
from pathlib import Path
import torch
from models.bisenet.model import BiSeNet

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = str(BASE_DIR / "models" / "bisenet" / "79999_iter.pth")


def load_bisenet():

    model = BiSeNet(n_classes=19)

    state_dict = torch.load(
        MODEL_PATH,
        map_location="cpu"
    )

    model.load_state_dict(state_dict)

    model.eval()

    return model