import os
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import torch
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
pinecone_index_name = "influencer-submission"

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)
if pinecone_index_name not in pc.list_indexes().names():
    pc.create_index(
        name=pinecone_index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=pinecone_env),
    )
index = pc.Index(pinecone_index_name)

# Load CLIP model
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")


def screenshot_milanote_board(board_url: str, save_path: str) -> str:
    print(f"Capturing screenshot from: {board_url}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(board_url, wait_until="networkidle", timeout=60000)
        page.screenshot(path=save_path, full_page=True)
        browser.close()
    print(f"Screenshot saved: {save_path}")
    return save_path


# User input for Milanote board
image_url = "https://app.milanote.com/1TLhVS1BNzwSe9?p=2NR3mpeg4Gp"
image_path = f"temp_screenshot_{uuid.uuid4().hex}.png"

try:
    screenshot_milanote_board(image_url, image_path)
    image = Image.open(image_path).convert("RGB")
except Exception as e:
    print(f"Error loading image: {e}")
    exit(1)

# Generate CLIP embedding
print("Generating image embedding...")
inputs = clip_processor(images=image, return_tensors="pt")
with torch.no_grad():
    image_features = clip_model.get_image_features(**inputs)
embedding = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
vector = embedding[0].tolist()

# Pad to Pinecone dimension (1536)
vector = vector + [0.0] * (1536 - len(vector)) if len(vector) < 1536 else vector[:1536]

# Upsert to Pinecone
image_id = f"image_{uuid.uuid4().hex}"
index.upsert(
    namespace="image-submission",
    vectors=[{"id": image_id, "values": vector, "metadata": {"source": image_url}}],
)

# Query relevant brief
print("Querying most relevant brief...")
query_response = index.query(
    namespace="brief", vector=vector, top_k=1, include_metadata=True
)
if not query_response.matches:
    print("No matching brief found for image submission.")
    exit(1)
most_relevant_brief = query_response.matches[0].metadata.get("chunk_text", "")

# Load evaluation prompts
prompt_path = Path("data/brief_prompt_questions.json")
if not prompt_path.exists():
    print("brief_prompt_questions.json not found.")
    exit(1)
prompt_data = json.loads(prompt_path.read_text(encoding="utf-8"))
prompts = (
    prompt_data if isinstance(prompt_data, list) else prompt_data.get("prompts", [])
)

# Select top 3 image/general prompts
submission_type = "image"
relevant_prompts = [p for p in prompts if p.get("type") in [submission_type, "general"]]
selected_prompts = relevant_prompts[:3]

prompt_blocks = "\n".join(
    [
        f"{i+1}. {p['question']}\n- Corrections:\n- What went well:"
        for i, p in enumerate(selected_prompts)
    ]
)

# Create final prompt
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
    f"Submission URL:\n{image_url}\n\n"
    f"Questions:\n{prompt_blocks}\n"
)

# Run OpenAI GPT-4 Turbo chat
print("Running GPT-4 evaluation...")
client = OpenAI(api_key=openai_api_key)
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {"role": "system", "content": "You evaluate influencer submissions."},
        {"role": "user", "content": combined_prompt},
    ],
)

output = response.choices[0].message.content

# Save results
results_dir = Path("data/results")
results_dir.mkdir(exist_ok=True)
output_file = results_dir / f"{image_id}_eval.json"
output_file.write_text(json.dumps({"evaluation": output}, indent=2), encoding="utf-8")
print(f"Evaluation complete. Saved to: {output_file}")

# Cleanup
if os.path.exists(image_path):
    os.remove(image_path)
