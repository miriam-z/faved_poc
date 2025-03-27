from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import evaluate_text, evaluate_video, evaluate_image
from config import print_config_status

app = FastAPI(
    title="Influencer Submission Evaluator",
    description="API for evaluating influencer submissions against brand briefs",
    version="0.1.0",
)

# Print configuration status on startup
print_config_status()

# CORS config — allow frontend (Next.js) to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update this for production domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(evaluate_text.router, prefix="/text", tags=["Text Evaluation"])
app.include_router(evaluate_image.router, prefix="/image", tags=["Image Evaluation"])
app.include_router(evaluate_video.router, prefix="/video", tags=["Video Evaluation"])


@app.get("/")
def root():
    return {"status": "running", "version": "0.1"}
