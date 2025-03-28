import os
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_relevant_brief
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from playwright.sync_api import sync_playwright
import tempfile

router = APIRouter()

# Initialize CLIP model and processor globally
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")


class ImageSubmission(BaseModel):
    image_url: str


class EvaluationResponse(BaseModel):
    evaluation: dict


def screenshot_milanote_board(board_url: str) -> str:
    """Take a screenshot of a Milanote board and return the path to the temporary file."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(board_url, wait_until="networkidle", timeout=60000)
            page.screenshot(path=temp_file.name, full_page=True)
            browser.close()
        return temp_file.name
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise HTTPException(
            status_code=500, detail=f"Failed to capture screenshot: {str(e)}"
        )


def get_image_embedding(image_path: str) -> list[float]:
    """Get CLIP embedding for an image."""
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = clip_processor(images=image, return_tensors="pt")

        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)
        embedding = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        vector = embedding[0].tolist()

        # Pad to Pinecone dimension (1536)
        return (
            vector + [0.0] * (1536 - len(vector))
            if len(vector) < 1536
            else vector[:1536]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process image: {str(e)}"
        )


@router.post("/", response_model=EvaluationResponse)
async def evaluate_image_submission(submission: ImageSubmission):
    try:
        # Take screenshot of Milanote board
        temp_image_path = screenshot_milanote_board(submission.image_url)

        try:
            # Initialize Pinecone
            index = init_pinecone()

            # Get image embedding
            image_embedding = get_image_embedding(temp_image_path)

            # Generate unique ID for the submission
            image_id = f"image_{uuid.uuid4().hex}"

            # Upsert to Pinecone
            index.upsert(
                namespace="image-submission",
                vectors=[
                    {
                        "id": image_id,
                        "values": image_embedding,
                        "metadata": {"source": submission.image_url},
                    }
                ],
            )

            # Get relevant brief
            most_relevant_brief = get_relevant_brief(index, image_embedding)

            # Load prompt questions
            prompt_path = Path(BRIEF_PROMPT_PATH)
            if not prompt_path.exists():
                raise HTTPException(
                    status_code=404, detail="Prompt questions file not found"
                )

            prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
            prompts = (
                prompt_data
                if isinstance(prompt_data, list)
                else prompt_data.get("prompts", [])
            )

            # Filter relevant prompts
            submission_type = "image"
            relevant_prompts = [
                p
                for p in prompts
                if p.get("type") in [submission_type, "general", "image"]
            ]
            selected_prompts = relevant_prompts[:3]

            prompt_blocks = "\n".join(
                [
                    f"{i+1}. {p['question']}\n- Corrections:\n- What went well:"
                    for i, p in enumerate(selected_prompts)
                ]
            )

            # Create evaluation prompt
            combined_prompt = (
                "You are a brand evaluating influencer image-based submissions.\n"
                "Given:\n"
                "1. A campaign brief\n"
                "2. A submission (Milanote board screenshot)\n"
                "3. A list of evaluation questions\n\n"
                "Evaluate internally using all relevant questions but output only the top 3 most relevant questions.\n"
                "For each selected question:\n"
                "- Provide bullet points for 'corrections' (if any), or write 'No corrections needed'\n"
                "- Provide bullet points for 'what went well'\n\n"
                "At the end, include a final summary with:\n"
                "- Top-level corrections\n"
                "- What the influencer did well\n"
                "- A decision: 'ACCEPT' or 'REJECT' (must be one)\n\n"
                "Respond in this JSON format:\n"
                '{\n  "questions": [\n    {"question": "...", "corrections": "...", "what_went_well": "..."},\n    ...\n  ],\n  "summary": {\n    "corrections": "...",\n    "what_went_well": "...",\n    "decision": "ACCEPT" or "REJECT"\n  }\n}\n\n'
                f"Brief:\n{most_relevant_brief}\n\n"
                f"Submission URL:\n{submission.image_url}\n\n"
                f"Questions:\n{prompt_blocks}\n"
            )

            # Get evaluation from GPT-4
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You evaluate influencer submissions.",
                    },
                    {"role": "user", "content": combined_prompt},
                ],
            )

            evaluation = json.loads(response.choices[0].message.content)
            return EvaluationResponse(evaluation=evaluation)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Failed to parse evaluation response"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
