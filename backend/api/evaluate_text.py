from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_embedding, get_relevant_brief
import json
from pathlib import Path
import uuid

router = APIRouter()


class TextSubmission(BaseModel):
    text: str


class EvaluationResponse(BaseModel):
    evaluation: dict


@router.post("/", response_model=EvaluationResponse)
async def evaluate_text_submission(submission: TextSubmission):
    try:
        # Initialize Pinecone
        index = init_pinecone()

        # Get embedding for submission text
        submission_embedding = get_embedding(submission.text)

        # Generate unique ID for submission
        submission_id = f"text_{uuid.uuid4().hex}"
        print(f"Upserting text submission with ID: {submission_id}")

        try:
            # Upsert submission to Pinecone
            index.upsert(
                namespace="text-submission",
                vectors=[
                    {
                        "id": submission_id,
                        "values": submission_embedding,
                        "metadata": {
                            "chunk_text": submission.text,
                            "source": "submission",
                        },
                    }
                ],
            )
            print(f"Successfully upserted text submission: {submission_id}")

            # Verify upsert by checking stats
            stats = index.describe_index_stats()
            print(f"Index stats after upsert: {stats}")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upsert text submission: {str(e)}"
            )

        # Get relevant brief
        most_relevant_brief = get_relevant_brief(index, submission_embedding)

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
        submission_type = "text"
        relevant_prompts = [
            p
            for p in prompts
            if p.get("type") in [submission_type, "general", "script"]
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
            "You are a brand evaluating influencer submissions.\n"
            "You are given:\n"
            "1. A campaign brief (summarized).\n"
            "2. A submission from an influencer (text).\n"
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
            f"Submission:\n{submission.text}\n\n"
            f"Questions:\n{prompt_blocks}\n"
        )

        # Get evaluation from GPT-4
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that evaluates influencer content. You MUST respond with valid JSON in the exact format specified. Do not include any additional text or formatting outside of the JSON structure.",
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

            required_summary_keys = {"corrections", "what_went_well", "decision"}
            if not all(key in evaluation["summary"] for key in required_summary_keys):
                raise ValueError("Summary missing required keys")

            print("Successfully validated JSON response structure")
            return EvaluationResponse(evaluation=evaluation)

        except json.JSONDecodeError as je:
            print(f"JSON parse error at position {je.pos}: {je.msg}")
            print(f"Content around error: {raw_content[max(0, je.pos-50):je.pos+50]}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse GPT-4 response as JSON. Error: {str(je)}",
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=500, detail=f"Invalid response structure: {str(ve)}"
            )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate evaluation: {str(e)}"
        )
