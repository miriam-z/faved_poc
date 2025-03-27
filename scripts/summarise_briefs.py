import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- Config ---
BRIEFS_DIR = Path("data/brief")
OUTPUT_JSON = Path("data/summaries/briefs_summaries.json")
OUTPUT_TXT = Path("data/summaries/briefs_summaries.txt")


def extract_title(text):
    """Extract a meaningful title from the first 5 lines of the brief."""
    lines = text.strip().split("\n")[:5]
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    # Select the line with the most words
    if non_empty_lines:
        return max(non_empty_lines, key=lambda line: len(line.split()))
    return "untitled"


def build_summary_prompt(brief_text):
    return f"""
You are an expert in summarizing brand briefs for influencer collaborations.

Summarize the following brand brief clearly and concisely so it can be embedded later for evaluation:

Brief:
{brief_text}

Respond with only the summary, no title or explanation.
"""


def main():
    summaries = []
    flat_summaries = []

    # Create output directories if they don't exist
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)

    for file_path in BRIEFS_DIR.glob("*.txt"):
        brief_text = file_path.read_text(encoding="utf-8").strip()
        title = extract_title(brief_text)

        prompt = build_summary_prompt(brief_text)
        print(f"Summarizing: {file_path.name}")

        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You summarize brand briefs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            summary = response.choices[0].message.content.strip()
            full_summary = f"{title}: {summary}"
            summaries.append({"file": file_path.name, "summary": full_summary})
            flat_summaries.append(full_summary)

        except Exception as e:
            print(f"Error summarizing {file_path.name}: {e}")
            summaries.append({"file": file_path.name, "summary": "", "error": str(e)})

    OUTPUT_JSON.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    OUTPUT_TXT.write_text("\n\n".join(flat_summaries), encoding="utf-8")
    print(f"Saved summaries to {OUTPUT_JSON} and flat text to {OUTPUT_TXT}")


if __name__ == "__main__":
    main()


# Version 2 : Improved process for summarising briefs

# import os
# import json
# from pathlib import Path
# from openai import OpenAI
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")
# client = OpenAI(api_key=api_key)

# # Config
# BRIEFS_DIR = Path("data/brief")
# OUTPUT_JSON = Path("data/summaries/briefs_summaries.json")
# OUTPUT_TXT = Path("data/summaries/briefs_summaries.txt")
# OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# print("Reading briefs...")
# brief_texts = []
# for path in sorted(BRIEFS_DIR.glob("*.txt")):
#     text = path.read_text(encoding="utf-8").strip()
#     if text:
#         brief_texts.append(f"### {path.name}\n{text}")

# combined_input = "\n\n".join(brief_texts)

# print("Summarizing all briefs together...")
# try:
#     response = client.chat.completions.create(
#         model="gpt-4-turbo-preview",
#         messages=[
#             {
#                 "role": "system",
#                 "content": "You are an expert in summarizing brand briefs for influencer collaborations.",
#             },
#             {
#                 "role": "user",
#                 "content": f"""
# You are an expert in summarizing brand briefs for influencer collaborations.

# Summarize the following brand briefs clearly and concisely so they can be embedded later for evaluation:

# {combined_input}

# Respond with only the summaries, no titles or explanations.
# """,
#             },
#         ],
#     )
#     summary = response.choices[0].message.content.strip()

#     OUTPUT_TXT.write_text(summary, encoding="utf-8")
#     OUTPUT_JSON.write_text(json.dumps({"summary": summary}, indent=2), encoding="utf-8")

#     print(f"Summary saved to:\n- {OUTPUT_TXT}\n- {OUTPUT_JSON}")

# except Exception as e:
#     print(f"Error summarizing briefs: {e}")
