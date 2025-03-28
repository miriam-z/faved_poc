import os
import json
import uuid
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_relevant_brief
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from playwright.async_api import async_playwright
import tempfile
import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

router = APIRouter()

# Initialize CLIP model and processor globally
try:
    print("Initializing CLIP model and processor...")
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    print("CLIP model initialized successfully")
except Exception as e:
    print(f"Error initializing CLIP model: {e}")
    raise RuntimeError(f"Failed to initialize CLIP model: {e}")


class ImageSubmission(BaseModel):
    image_url: str

    @field_validator("image_url")
    @classmethod
    def validate_milanote_url(cls, v):
        if not v.startswith("https://app.milanote.com/"):
            raise ValueError("URL must be a valid Milanote board URL")
        return v


class EvaluationResponse(BaseModel):
    evaluation: dict


async def screenshot_milanote_board(board_url: str) -> str:
    """Take a screenshot of a Milanote board and return the path to the temporary file."""
    print(f"Capturing screenshot from: {board_url}")
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Set viewport size to ensure consistent capture
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.goto(board_url, wait_until="networkidle", timeout=60000)
            await page.screenshot(path=temp_file.name, full_page=True)
            await browser.close()
        print(f"Screenshot saved to: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        print(f"Screenshot error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to capture screenshot: {str(e)}"
        )


def validate_image(image_path: str) -> None:
    """Validate image size and format."""
    try:
        with Image.open(image_path) as img:
            # Check format
            if img.format not in ["PNG", "JPEG", "JPG"]:
                raise ValueError(f"Unsupported image format: {img.format}")

            # Check dimensions
            width, height = img.size
            if width < 100 or height < 100:
                raise ValueError(f"Image too small: {width}x{height}")
            if width > 10000 or height > 10000:
                raise ValueError(f"Image too large: {width}x{height}")

            # Check file size
            file_size = os.path.getsize(image_path) / (1024 * 1024)  # Size in MB
            if file_size > 50:
                raise ValueError(f"File too large: {file_size:.1f}MB")
    except Exception as e:
        raise ValueError(f"Image validation failed: {str(e)}")


def get_image_embedding(image_path: str) -> list[float]:
    """Get CLIP embedding for an image."""
    print("Generating image embedding...")
    try:
        # Validate image before processing
        validate_image(image_path)

        image = Image.open(image_path).convert("RGB")
        inputs = clip_processor(images=image, return_tensors="pt")

        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)
        embedding = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        vector = embedding[0].tolist()

        # Pad to Pinecone dimension (1536)
        vector = (
            vector + [0.0] * (1536 - len(vector))
            if len(vector) < 1536
            else vector[:1536]
        )
        print("Image embedding generated successfully")
        return vector
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process image: {str(e)}"
        )


@router.post("/", response_model=EvaluationResponse)
async def evaluate_image_submission(submission: ImageSubmission):
    """Evaluate an image submission from a Milanote board.

    Args:
        submission: ImageSubmission object containing the Milanote board URL

    Returns:
        EvaluationResponse containing the evaluation results

    Raises:
        HTTPException: If any step in the evaluation process fails
    """
    temp_image_path = None
    try:
        print(f"Starting evaluation for submission: {submission.image_url}")

        # Take screenshot of Milanote board
        try:
            temp_image_path = await screenshot_milanote_board(submission.image_url)
            print(f"Successfully captured screenshot: {temp_image_path}")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to capture Milanote board: {str(e)}"
            )

        try:
            # Initialize Pinecone
            index = init_pinecone()
            print("Successfully initialized Pinecone index")

            # Get image embedding
            try:
                image_embedding = get_image_embedding(temp_image_path)
                print("Successfully generated image embedding")
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate image embedding: {str(e)}",
                )

            # Generate unique ID for the submission
            image_id = f"image_{uuid.uuid4().hex}"
            print(f"Generated submission ID: {image_id}")

            try:
                # Upsert to Pinecone with timestamp and metadata
                timestamp = datetime.datetime.now(datetime.UTC)
                index.upsert(
                    namespace="image-submission",
                    vectors=[
                        {
                            "id": image_id,
                            "values": image_embedding,
                            "metadata": {
                                "source": submission.image_url,
                                "type": "milanote_board",
                                "timestamp": str(timestamp),
                                "submission_type": "image",
                            },
                        }
                    ],
                )
                print(f"Successfully upserted image submission: {image_id}")

                # Verify upsert by checking stats
                stats = index.describe_index_stats()
                print(f"Index stats after upsert: {stats}")

            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upsert image submission: {str(e)}",
                )

            try:
                # Get relevant brief
                most_relevant_brief = get_relevant_brief(index, image_embedding)
                if not most_relevant_brief:
                    raise HTTPException(
                        status_code=404,
                        detail="No matching brief found for the submission",
                    )
                print("Successfully retrieved relevant brief")
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve relevant brief: {str(e)}",
                )

            # Load and validate prompt questions
            try:
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

                if not prompts:
                    raise HTTPException(
                        status_code=500, detail="No evaluation prompts found"
                    )
                print("Successfully loaded prompt questions")
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=500, detail="Failed to parse prompt questions file"
                )

            # Filter relevant prompts
            submission_type = "image"
            relevant_prompts = [
                p
                for p in prompts
                if p.get("type") in [submission_type, "general", "image"]
            ]
            if not relevant_prompts:
                raise HTTPException(
                    status_code=500,
                    detail="No relevant prompts found for image submission",
                )

            selected_prompts = relevant_prompts[:3]
            print(f"Selected {len(selected_prompts)} relevant prompts")

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

            print("Getting evaluation from GPT-4...")
            try:
                # Get evaluation from GPT-4
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-4-turbo-preview",  # Using the latest model
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI that evaluates influencer image-based submissions. You MUST respond with valid JSON in the exact format specified. Do not include any additional text or formatting outside of the JSON structure.",
                        },
                        {"role": "user", "content": combined_prompt},
                    ],
                    temperature=0.2,  # Lower temperature for more consistent JSON formatting
                    max_tokens=2000,
                    response_format={"type": "json_object"},  # Enforce JSON response
                )

                # Debug: Print raw response content
                raw_content = response.choices[0].message.content
                print("Raw GPT-4 response:")
                print(raw_content)

                if not raw_content or raw_content.isspace():
                    raise HTTPException(
                        status_code=500, detail="Received empty response from GPT-4"
                    )

                try:
                    evaluation = json.loads(raw_content)

                    # Validate response structure
                    required_keys = {"questions", "summary"}
                    if not all(key in evaluation for key in required_keys):
                        raise ValueError(
                            "Response missing required keys: questions and/or summary"
                        )

                    if not isinstance(evaluation["questions"], list):
                        raise ValueError("'questions' must be a list")

                    if not isinstance(evaluation["summary"], dict):
                        raise ValueError("'summary' must be an object")

                    required_summary_keys = {
                        "corrections",
                        "what_went_well",
                        "decision",
                    }
                    if not all(
                        key in evaluation["summary"] for key in required_summary_keys
                    ):
                        raise ValueError("Summary missing required keys")

                    print("Successfully validated JSON response structure")
                    return EvaluationResponse(evaluation=evaluation)

                except json.JSONDecodeError as je:
                    print(f"JSON parse error at position {je.pos}: {je.msg}")
                    print(
                        f"Content around error: {raw_content[max(0, je.pos-50):je.pos+50]}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to parse GPT-4 response as JSON. Error: {str(je)}",
                    )
                except ValueError as ve:
                    raise HTTPException(
                        status_code=500, detail=f"Invalid response structure: {str(ve)}"
                    )

            except Exception as e:
                print(f"Error generating evaluation: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to generate evaluation: {str(e)}"
                )

        finally:
            # Clean up temporary file
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.unlink(temp_image_path)
                    print(f"Cleaned up temporary file: {temp_image_path}")
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary file: {e}")

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Failed to parse evaluation response"
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as is
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during evaluation: {str(e)}"
        )
