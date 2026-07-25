from fastapi import FastAPI, UploadFile, File
from utils.image_reader import read_image
from image_validation.validator import validate_blur, validate_brightness,validate_face
import shutil
import os

app = FastAPI()

UPLOAD_FOLDER ="uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
def home():
    return{
        "message": "Welcome to SkinWise AI Backend!"
    }

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_info = read_image(file_path)
    blur_results = validate_blur(file_path)
    brightness_result = validate_brightness(file_path)
    detected_face = validate_face(file_path)

    return{
        "filename": file.filename,
        "image_info": image_info,
        "blur_results": blur_results,
        "brightness_result": brightness_result,
        "detected_face": detected_face
    }
