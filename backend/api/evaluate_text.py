from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class TextSubmission(BaseModel):
    text: str


@router.post("/")
async def evaluate_text_submission(submission: TextSubmission):
    return {
        "message": "Text evaluation endpoint - To be implemented",
        "received": submission.text,
    }
