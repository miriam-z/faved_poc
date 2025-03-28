import os
import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_embedding, get_relevant_brief
from youtube_transcript_api import YouTubeTranscriptApi
import datetime

router = APIRouter()


class VideoSubmission(BaseModel):
    youtube_url: str

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v):
        if not re.search(r"(?:v=|youtu.be/)([\w-]{11})", v):
            raise ValueError("Invalid YouTube URL format")
        return v


class EvaluationResponse(BaseModel):
    evaluation: dict


def get_video_id(youtube_url: str) -> str:
    """Extract video ID from YouTube URL."""
    video_id_match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", youtube_url)
    if not video_id_match:
        raise ValueError("Could not extract video ID from URL")
    return video_id_match.group(1)


def get_video_transcript(video_id: str) -> str:
    """Fetch and combine transcript segments from YouTube video."""
    try:
        print(f"Fetching transcript for video ID: {video_id}")
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([item["text"] for item in transcript_data])
        print("Transcript fetched successfully")
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        raise ValueError(f"Failed to fetch video transcript: {str(e)}")


@router.post("/", response_model=EvaluationResponse)
async def evaluate_video_submission(submission: VideoSubmission):
    """Evaluate a video submission from YouTube.

    Args:
        submission: VideoSubmission object containing the YouTube URL

    Returns:
        EvaluationResponse containing the evaluation results

    Raises:
        HTTPException: If any step in the evaluation process fails
    """
    try:
        print(f"Starting evaluation for submission: {submission.youtube_url}")

        # Extract video ID and get transcript
        try:
            video_id = get_video_id(submission.youtube_url)
            transcript = get_video_transcript(video_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to process video submission: {str(e)}"
            )

        # Initialize Pinecone and get embedding
        try:
            index = init_pinecone()
            print("Successfully initialized Pinecone index")

            # Get embedding for transcript
            transcript_embedding = get_embedding(transcript)
            print("Successfully generated transcript embedding")

            # Upsert to Pinecone with timestamp and metadata
            timestamp = datetime.datetime.now(datetime.UTC)
            index.upsert(
                namespace="video-submission",
                vectors=[
                    {
                        "id": video_id,
                        "values": transcript_embedding,
                        "metadata": {
                            "chunk_text": transcript,
                            "source": submission.youtube_url,
                            "type": "youtube_video",
                            "timestamp": str(timestamp),
                            "submission_type": "video",
                        },
                    }
                ],
            )
            print(f"Successfully upserted video submission: {video_id}")

            # Verify upsert by checking stats
            stats = index.describe_index_stats()
            print(f"Index stats after upsert: {stats}")

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process video with Pinecone: {str(e)}",
            )

        # Get relevant brief
        try:
            most_relevant_brief = get_relevant_brief(index, transcript_embedding)
            if not most_relevant_brief:
                raise HTTPException(
                    status_code=404, detail="No matching brief found for the submission"
                )
            print("Successfully retrieved relevant brief")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve relevant brief: {str(e)}"
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
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to load prompt questions: {str(e)}"
            )

        # Filter relevant prompts
        submission_type = "video"
        relevant_prompts = [
            p for p in prompts if p.get("type") in [submission_type, "general"]
        ]
        if not relevant_prompts:
            raise HTTPException(
                status_code=500, detail="No relevant prompts found for video submission"
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
            "You are a brand evaluating influencer submissions.\n"
            "You are given:\n"
            "1. A campaign brief (summarized).\n"
            "2. A submission from an influencer (a YouTube video transcript).\n"
            "3. A list of relevant evaluation questions.\n\n"
            "Evaluate the submission using all relevant questions internally,\n"
            "but only output detailed answers for the top 3 most relevant questions.\n"
            "For each selected question:\n"
            "- Provide a short bullet point for 'corrections' (if any). If none, write 'No corrections needed'.\n"
            "- Provide a short bullet point for 'what went well'.\n\n"
            "At the end, include a final summary with:\n"
            "- Top-level corrections.\n"
            "- What the influencer did well.\n"
            "- A decision: 'ACCEPT' or 'REJECT' (strictly one of these only).\n"
            "Respond in this exact JSON format:\n"
            '{\n  "questions": [\n    {"question": "...", "corrections": "...", "what_went_well": "..."},\n    ...\n  ],\n  "summary": {\n    "corrections": "...",\n    "what_went_well": "...",\n    "decision": "ACCEPT" or "REJECT"\n  }\n}\n\n'
            f"Brief:\n{most_relevant_brief}\n\n"
            f"Submission:\n{transcript}\n\n"
            f"Questions:\n{prompt_blocks}\n"
        )

        print("Getting evaluation from GPT-4...")
        try:
            # Get evaluation from GPT-4
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI that evaluates influencer content. You MUST respond with valid JSON in the exact format specified. Do not include any additional text or formatting outside of the JSON structure.",
                    },
                    {
                        "role": "user",
                        "content": combined_prompt,
                    },
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

                required_summary_keys = {"corrections", "what_went_well", "decision"}
                if not all(
                    key in evaluation["summary"] for key in required_summary_keys
                ):
                    raise ValueError("Summary missing required keys")

                print("Successfully validated JSON response structure")

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

            print("Successfully generated evaluation")
            return EvaluationResponse(evaluation=evaluation)

        except Exception as e:
            print(f"Error generating evaluation: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to generate evaluation: {str(e)}"
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as is
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during evaluation: {str(e)}"
        )
