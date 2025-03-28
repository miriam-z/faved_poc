from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from config import OPENAI_API_KEY, BRIEF_PROMPT_PATH
from utils import init_pinecone, get_embedding, get_relevant_brief
import json
from pathlib import Path

router = APIRouter()

# testing path: to be deleted start

print(f"Prompt path: {BRIEF_PROMPT_PATH}")

if not BRIEF_PROMPT_PATH.exists():
    raise HTTPException(status_code=404, detail="Prompt questions file not found")
# testing path: to be deleted end


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

        # Upsert submission to Pinecone
        submission_id = "text_submission"  # You might want to generate a unique ID
        index.upsert(
            namespace="text-submission",
            vectors=[
                {
                    "id": submission_id,
                    "values": submission_embedding,
                    "metadata": {"chunk_text": submission.text, "source": "submission"},
                }
            ],
        )

        # Get relevant brief
        most_relevant_brief = get_relevant_brief(index, submission_embedding)

        # Load prompt questions
        # prompt_path = Path("data/brief_prompt_questions.json")
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You evaluate influencer content."},
                {"role": "user", "content": combined_prompt},
            ],
        )

        evaluation = json.loads(response.choices[0].message.content)
        return EvaluationResponse(evaluation=evaluation)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Failed to parse evaluation response"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
