import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
pinecone_index_name = "influencer-submission"

# Initialize Pinecone client
pc = Pinecone(api_key=pinecone_api_key)

# Create index if it doesn't exist
if pinecone_index_name not in pc.list_indexes().names():
    pc.create_index(
        name=pinecone_index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=pinecone_env),
    )

index = pc.Index(pinecone_index_name)

# Load and embed submission
submissions_dir = Path("data/submissions")
submission_files = list(submissions_dir.glob("*.txt"))
if not submission_files:
    print("No submission files found.")
    exit(1)

submission_path = submission_files[0]
submission_text = submission_path.read_text(encoding="utf-8").strip()
submission_id = submission_path.stem  # Extract filename without extension

client = OpenAI(api_key=openai_api_key)
submission_embedding = (
    client.embeddings.create(input=[submission_text], model="text-embedding-3-small")
    .data[0]
    .embedding
)

# Upsert submission embedding into Pinecone under "submissions" namespace
index.upsert(
    namespace="text-submission",
    vectors=[
        {
            "id": submission_id,
            "values": submission_embedding,
            "metadata": {"chunk_text": submission_text, "source": "submission"},
        }
    ],
)

# Wait to ensure consistency
time.sleep(10)

# Query Pinecone to find the most relevant brief from the default namespace
query_response = index.query(
    vector=submission_embedding,
    top_k=1,
    namespace="brief",
    include_metadata=True,
)

if not query_response.matches:
    print("No matching brief found for submission.")
    exit(1)

most_relevant_brief = query_response.matches[0].metadata.get("chunk_text", "")

# Load prompt questions
prompt_path = Path("data/brief_prompt_questions.json")
if not prompt_path.exists():
    print("brief_prompt_questions.json not found.")
    exit(1)

prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
if isinstance(prompt_data, list):
    prompts = prompt_data
else:
    prompts = prompt_data.get("prompts", [])

# Determine type of submission and filter relevant prompts
submission_type = "script"  # default for .txt
submission_ext = submission_path.suffix
if submission_ext == ".mp4":
    submission_type = "video"
elif submission_ext in [".jpg", ".jpeg", ".png"]:
    submission_type = "image"

# All relevant prompts filtered first, only top 3 used in final output
relevant_prompts = [p for p in prompts if p.get("type") in [submission_type, "general"]]

# Build structured evaluation prompt for top 3
selected_prompts = relevant_prompts[:3]
prompt_blocks = "\n".join(
    [
        f"{i+1}. {p['question']}\n- Corrections:\n- What went well:"
        for i, p in enumerate(selected_prompts)
    ]
)

combined_prompt = (
    "You are a brand evaluating influencer submissions.\n"
    "You are given:\n"
    "1. A campaign brief (summarized).\n"
    "2. A submission from an influencer.\n"
    "3. A list of relevant evaluation questions.\n\n"
    "Evaluate the submission only using the questions listed.\n"
    "For each question:\n"
    "- Provide a short bullet point for 'corrections' (if any).\n"
    "- Provide a short bullet point for 'what went well'.\n\n"
    "At the end, include a final summary with:\n"
    "- Top-level corrections.\n"
    "- What the influencer did well.\n"
    "- A decision: 'ACCEPT' or 'REJECT' (strictly one of these only).\n"
    "Respond in this exact JSON format:\n"
    '{\n  "questions": [\n    {"question": "...", "corrections": "...", "what_went_well": "..."},\n    ...\n  ],\n  "summary": {\n    "corrections": "...",\n    "what_went_well": "...",\n    "decision": "ACCEPT" or "REJECT"\n  }\n}\n\n'
    f"Brief:\n{most_relevant_brief}\n\n"
    f"Submission:\n{submission_text}\n\n"
    f"Questions:\n{prompt_blocks}\n"
)

# Send evaluation to GPT
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You evaluate influencer content."},
        {"role": "user", "content": combined_prompt},
    ],
)

output = response.choices[0].message.content

# Save output
results_dir = Path("data/results")
results_dir.mkdir(exist_ok=True)
output_file = results_dir / f"{submission_path.name}_eval.json"
output_file.write_text(json.dumps({"evaluation": output}, indent=2), encoding="utf-8")

print(f"Evaluation complete. Saved to {output_file}")
