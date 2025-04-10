import os
import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_embedding, get_relevant_brief
from youtube_transcript_api import YouTubeTranscriptApi
import datetime
import tempfile
import cv2  # OpenCV for frame processing
import io

router = APIRouter()


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


def summarize_transcript(transcript: str) -> str:
    # Use OpenAI to summarize the transcript
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Summarize the following transcript."},
            {"role": "user", "content": transcript},
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def extract_video_transcript(video_path: str) -> str:
    # Extract audio from video using ffmpeg
    audio_path = video_path.replace('.mp4', '.wav')
    os.system(f"ffmpeg -i {video_path} -q:a 0 -map a {audio_path}")

    # Transcribe audio using OpenAI
    client = OpenAI()
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file
        )

    # Clean up audio file
    os.remove(audio_path)

    return transcription.text


def extract_video_frames(video_path: str) -> list:
    """Extract frames from the video for analysis."""
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    success, frame = cap.read()
    count = 0
    while success:
        if count % int(frame_rate) == 0:  # Sample one frame per second
            frames.append(frame)
        success, frame = cap.read()
        count += 1
    cap.release()
    return frames


def analyze_frames(frames: list) -> list:
    """Analyze each frame and return analysis results."""
    analysis_results = []
    for frame in frames:
        # Reduce resolution
        small_frame = cv2.resize(frame, (320, 240))
        gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate average pixel intensity
        avg_intensity = gray_frame.mean()
        
        # Detect edges using Canny edge detection
        edges = cv2.Canny(gray_frame, 100, 200)
        
        # Count the number of edges
        edge_count = cv2.countNonZero(edges)
        
        # Example: Detect faces using a pre-trained Haar Cascade classifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        face_count = len(faces)
        
        # Append analysis results for the frame
        analysis_results.append({
            "avg_intensity": avg_intensity,
            "edge_count": edge_count,
            "face_count": face_count
        })
    return analysis_results


def extract_video_thumbnails(video_path: str) -> list:
    """Extract thumbnails from the video."""
    clip = VideoFileClip(video_path)
    duration = clip.duration
    # Extract a thumbnail every 10 seconds
    thumbnails = [clip.get_frame(t) for t in range(0, int(duration), 10)]
    return thumbnails


@router.post("/", response_model=EvaluationResponse)
async def evaluate_video_submission(file: UploadFile = File(...)):
    """Evaluate a video submission from an uploaded MP4 or MOV file."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.mp4', '.mp3', '.mov')):
            raise HTTPException(status_code=400, detail="Invalid file type. Only MP4, MP3, and MOV are supported.")

        # Save the uploaded file to a temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        try:
            with temp_file as f:
                f.write(await file.read())
            video_path = temp_file.name

            # Extract transcript and frames
            transcript = extract_video_transcript(video_path)
            summarized_transcript = summarize_transcript(transcript)
            frames = extract_video_frames(video_path)
            frame_analysis = analyze_frames(frames)

            # Initialize Pinecone and get embedding
            index = init_pinecone()
            print("Successfully initialized Pinecone index")

            # Get embedding for transcript
            transcript_embedding = get_embedding(summarized_transcript)
            print("Successfully generated transcript embedding")

            # Combine transcript and frame analysis for evaluation
            combined_analysis = {
                "transcript": summarized_transcript,
                "frame_analysis": frame_analysis
            }

            # Upsert to Pinecone with timestamp and metadata
            timestamp = datetime.datetime.now(datetime.UTC)
            index.upsert(
                namespace="video-submission",
                vectors=[
                    {
                        "id": file.filename,
                        "values": transcript_embedding,
                        "metadata": {
                            "chunk_text": json.dumps(combined_analysis),
                            "source": file.filename,
                            "type": "uploaded_video",
                            "timestamp": str(timestamp),
                            "submission_type": "video",
                        },
                    }
                ],
            )
            print(f"Successfully upserted video submission: {file.filename}")

            # Verify upsert by checking stats
            stats = index.describe_index_stats()
            print(f"Index stats after upsert: {stats}")

            # Get relevant brief
            most_relevant_brief = get_relevant_brief(index, transcript_embedding)
            if not most_relevant_brief:
                raise HTTPException(
                    status_code=404, detail="No matching brief found for the submission"
                )
            print("Successfully retrieved relevant brief")

            # Load and validate prompt questions
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
                "2. A submission from an influencer (a video transcript and frame analysis).\n"
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
                f"Submission:\n{json.dumps(combined_analysis)}\n\n"
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
            if os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    print(f"Cleaned up temporary file: {temp_file.name}")
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary file: {e}")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as is
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during evaluation: {str(e)}"
        )
