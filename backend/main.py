from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import evaluate_text, evaluate_video, evaluate_image
from config import print_config_status, DATA_DIR, BRIEF_PROMPT_PATH
from utils import setup_evaluation_system
import uvicorn
from pathlib import Path

# Print configuration status on startup
print_config_status()

# Initialize evaluation system before creating the app
print("\nInitializing evaluation system...")
setup_evaluation_system()

# Create FastAPI app after initialization
app = FastAPI(
    title="Influencer Submission Evaluator",
    description="API for evaluating influencer submissions against brand briefs",
    version="0.1.0",
)

# CORS config — allow frontend (Next.js) to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes after initialization is complete
app.include_router(evaluate_text.router, prefix="/text", tags=["Text Evaluation"])
app.include_router(evaluate_image.router, prefix="/image", tags=["Image Evaluation"])
app.include_router(evaluate_video.router, prefix="/video", tags=["Video Evaluation"])


@app.get("/")
def root():
    return {"status": "running", "version": "0.1.0"}


@app.get("/test/init")
def test_initialization():
    """Test endpoint to check initialization status."""
    briefs_dir = DATA_DIR / "brief"
    summaries_dir = DATA_DIR / "summaries"
    summaries_file = summaries_dir / "briefs_summaries.txt"

    status = {
        "briefs": {
            "directory_exists": briefs_dir.exists(),
            "brief_count": (
                len(list(briefs_dir.glob("*.txt"))) if briefs_dir.exists() else 0
            ),
        },
        "summaries": {
            "directory_exists": summaries_dir.exists(),
            "file_exists": summaries_file.exists(),
        },
        "prompts": {
            "file_exists": BRIEF_PROMPT_PATH.exists(),
        },
    }

    return {"status": "ok", "initialization_status": status}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
