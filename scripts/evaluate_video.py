import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import re

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

# Get YouTube link from user or test
youtube_url = "https://www.youtube.com/watch?v=DWbMS9KW8Vk"

# Extract video ID
video_id_match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", youtube_url)
if not video_id_match:
    print("Invalid YouTube URL")
    exit(1)

video_id = video_id_match.group(1)

# Fetch transcript
try:
    print("Fetching transcript...")
    transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
    print("Transcript fetched.")
    transcript = " ".join([item["text"] for item in transcript_data])
except Exception as e:
    print(f"Error fetching transcript: {e}")
    exit(1)

# Skip thumbnail
thumbnail_url = None

# Embed transcript
client = OpenAI(api_key=openai_api_key)
submission_embedding = (
    client.embeddings.create(input=[transcript], model="text-embedding-3-small")
    .data[0]
    .embedding
)

# Upsert submission embedding into Pinecone under "submissions" namespace
index.upsert(
    namespace="video-submission",
    vectors=[
        {
            "id": video_id,
            "values": submission_embedding,
            "metadata": {"chunk_text": transcript, "source": "youtube"},
        }
    ],
)

# Query Pinecone to find the most relevant brief from the default namespace
query_response = index.query(
    vector=submission_embedding, top_k=1, namespace="brief", include_metadata=True
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

# Filter only relevant prompts
submission_type = "video"
relevant_prompts = [p for p in prompts if p.get("type") in [submission_type, "general"]]

# Use top 3
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
    "2. A submission from an influencer (a YouTube video).\n"
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
output_file = results_dir / f"{video_id}_eval.json"
output_file.write_text(json.dumps({"evaluation": output}, indent=2), encoding="utf-8")

print(f"Evaluation complete. Saved to {output_file}")
