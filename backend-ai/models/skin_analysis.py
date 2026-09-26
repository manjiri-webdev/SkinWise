from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SkinAnalysisRecord(BaseModel):
    user_id: str
    created_at: datetime
    model_name: str
    model_version: str
    blackheads: int
    whiteheads: int
    papules: int
    pustules: int
    nodules: int
    dark_spots: int
    total_lesions: int
    severity: str
    severity_score: int
    detections_json: dict
