from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VideoSubmission(BaseModel):
    youtube_url: str


@router.post("/")
async def evaluate_video_submission(submission: VideoSubmission):
    return {
        "message": "Video evaluation endpoint - To be implemented",
        "received": submission.youtube_url,
    }
