import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
pinecone_index_name = "influencer-submission"  # Using standardized index name

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

# Load summaries from a single flat text file (briefs_summaries.txt)
summaries_file = Path("data/summaries/briefs_summaries.txt")
texts = []
ids = []
metadatas = []

if summaries_file.exists():
    content = summaries_file.read_text(encoding="utf-8").strip().split("\n\n")

    for i, chunk in enumerate(content):
        clean_text = chunk.strip()
        texts.append(clean_text)
        ids.append(f"brief_{i+1}")
        metadatas.append(
            {
                "source": "brief",
                "source_id": f"brief_{i+1}",
                "chunk_text": clean_text,
                "category": "brief",
                "length": len(clean_text.split()),
            }
        )
else:
    print("data/summaries/briefs_summaries.txt not found.")
    exit(1)

# Embed using OpenAI
client = OpenAI(api_key=openai_api_key)
response = client.embeddings.create(input=texts, model="text-embedding-3-small")
embeddings = [item.embedding for item in response.data]

# Upsert into Pinecone
vectors = [
    {"id": ids[i], "values": embeddings[i], "metadata": metadatas[i]}
    for i in range(len(texts))
]

index.upsert(namespace="brief", vectors=vectors)

time.sleep(10)  # Wait for vectors to be indexed

print("Embeddings uploaded to Pinecone successfully.")

# To delete the index from the command line, run:
# pc.delete_index(index_name)
