from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ImageSubmission(BaseModel):
    image_url: str


@router.post("/")
async def evaluate_image_submission(submission: ImageSubmission):
    return {
        "message": "Image evaluation endpoint - To be implemented",
        "received": submission.image_url,
    }
