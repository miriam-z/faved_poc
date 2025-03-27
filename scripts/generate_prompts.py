import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# --- Config ---
SUMMARY_FILE = Path("data/summaries/briefs_summaries.txt")
OUTPUT_FILE = Path("data/brief_prompt_questions.json")

PROMPT_TEMPLATE = """
You are a brand-submission strategist evaluating influencer submissions.

Based on all the brand brief summaries provided, generate 40 high-quality evaluation questions.
Split them into four categories, 10 each:

1. "script" — for evaluating draft scripts or text-based submissions
2. "video" — for evaluating video submissions
3. "image" — for evaluating visual or board-based submissions
4. "general" — for questions applicable to all types of submissions

Each question must be specific, measurable, and relevant.

IMPORTANT: Respond with ONLY a JSON array containing exactly 40 questions, 10 per category.
Use this exact format:
{
  "questions": [
    {"question": "...", "type": "script"},
    {"question": "...", "type": "video"},
    {"question": "...", "type": "image"},
    {"question": "...", "type": "general"}
  ]
}

Brief Summaries:
"""


def main():
    print("Reading brief summaries...")
    text = SUMMARY_FILE.read_text(encoding="utf-8")

    print("Generating prompts...")
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Using GPT-4 Turbo for better quality and speed
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON-only response generator specialized in creating evaluation questions from brand briefs.",
                },
                {"role": "user", "content": PROMPT_TEMPLATE + text},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        questions = result.get("questions", [])

        # Ensure we have questions of each type
        by_type = {"script": [], "video": [], "image": [], "general": []}
        for q in questions:
            q_type = q.get("type")
            if isinstance(q, dict) and q_type in by_type:
                by_type[q_type].append(q)

        # Take 10 questions from each category
        final_prompts = []
        for category, category_questions in by_type.items():
            final_prompts.extend(category_questions[:10])

        if final_prompts:
            OUTPUT_FILE.write_text(
                json.dumps(final_prompts, indent=2), encoding="utf-8"
            )
            print(f"Saved {len(final_prompts)} prompts to {OUTPUT_FILE}")
        else:
            print("No valid prompts were generated")

    except Exception as e:
        print(f"Error generating prompts: {str(e)}")


if __name__ == "__main__":
    main()
