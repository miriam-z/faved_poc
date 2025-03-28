from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
    DATA_DIR,
    BRIEF_PROMPT_PATH,
)
from fastapi import HTTPException
import json
from pathlib import Path
import asyncio
from typing import List, Dict
from tqdm import tqdm


def init_pinecone():
    """Initialize Pinecone client and ensure index exists."""
    try:
        # Initialize with API key
        pc = Pinecone(api_key=PINECONE_API_KEY)

        # Check if index exists
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
            print(f"Creating index: {PINECONE_INDEX_NAME}")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
            )

        # Get index instance
        index = pc.Index(PINECONE_INDEX_NAME)

        # Verify connection by getting stats
        try:
            stats = index.describe_index_stats()
            print(f"Connected to index. Stats: {stats}")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to index: {str(e)}"
            )

        return index

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize Pinecone: {str(e)}"
        )


def get_embedding(text: str) -> list[float]:
    """Get OpenAI embedding for text."""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        return (
            client.embeddings.create(input=[text], model="text-embedding-3-small")
            .data[0]
            .embedding
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate embedding: {str(e)}"
        )


def get_relevant_brief(index, submission_embedding: list[float]) -> str:
    """Query Pinecone to find the most relevant brief."""
    try:
        query_response = index.query(
            vector=submission_embedding,
            top_k=1,
            namespace="brief",
            include_metadata=True,
        )

        if not query_response.matches:
            raise HTTPException(
                status_code=404, detail="No matching brief found for submission."
            )

        return query_response.matches[0].metadata.get("chunk_text", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query brief: {str(e)}")


def generate_prompts(client: OpenAI) -> None:
    """Generate evaluation prompts from briefs."""
    try:
        summaries_file = DATA_DIR / "summaries/briefs_summaries.txt"
        if not summaries_file.exists():
            print("No brief summaries found. Skipping prompt generation.")
            return

        print("Reading brief summaries...")
        text = summaries_file.read_text(encoding="utf-8")

        print("Generating prompts...")
        prompt_template = """
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

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Using GPT-4 Turbo for better quality and speed
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON-only response generator specialized in creating evaluation questions from brand briefs.",
                },
                {"role": "user", "content": prompt_template + text},
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
            BRIEF_PROMPT_PATH.write_text(
                json.dumps(final_prompts, indent=2), encoding="utf-8"
            )
            print(f"Generated and saved {len(final_prompts)} evaluation prompts")
        else:
            print("No valid prompts were generated")

    except Exception as e:
        print(f"Error generating prompts: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate prompts: {str(e)}"
        )


async def process_brief_batch(
    client: OpenAI, briefs: List[Dict[str, str]], batch_size: int = 5
) -> List[Dict[str, str]]:
    """Process a batch of briefs concurrently."""
    summaries = []
    total = len(briefs)
    processed = 0

    for i in range(0, len(briefs), batch_size):
        batch = briefs[i : i + batch_size]
        results = []

        for brief in batch:
            prompt = f"""
            Summarize the following brand brief clearly and concisely so it can be embedded later for evaluation:
            Brief:
            {brief['text']}
            Respond with only the summary, no title or explanation.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You summarize brand briefs."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                summary = response.choices[0].message.content.strip()
                full_summary = f"{brief['title']}: {summary}"
                results.append({"file": brief["file"], "summary": full_summary})
                processed += 1
                print(f"Summarizing briefs: {(processed/total)*100:.0f}%", end="\r")
            except Exception as e:
                print(f"\nError summarizing {brief['file']}: {e}")
                continue

        summaries.extend(results)

    print("\nSummarization complete!")
    return summaries


async def summarize_briefs_async(client: OpenAI) -> None:
    """Asynchronously summarize briefs and create embeddings."""
    try:
        briefs_dir = DATA_DIR / "brief"
        summaries_dir = DATA_DIR / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        # First, collect all briefs
        briefs = []
        for file_path in briefs_dir.glob("*.txt"):
            brief_text = file_path.read_text(encoding="utf-8").strip()
            lines = brief_text.strip().split("\n")[:5]
            title = max((line.strip() for line in lines if line.strip()), key=len)
            briefs.append({"file": file_path.name, "text": brief_text, "title": title})

        if not briefs:
            print("No briefs found to process.")
            return

        print(f"Processing {len(briefs)} briefs...")
        summaries = await process_brief_batch(client, briefs)

        if summaries:
            # Save summaries
            summaries_json = summaries_dir / "briefs_summaries.json"
            summaries_txt = summaries_dir / "briefs_summaries.txt"

            # Prepare flat summaries for text file
            flat_summaries = [s["summary"] for s in summaries]

            # Save files
            summaries_json.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
            summaries_txt.write_text("\n\n".join(flat_summaries), encoding="utf-8")
            print(f"Generated summaries for {len(summaries)} briefs")
        else:
            print("No briefs were summarized")

    except Exception as e:
        print(f"Warning: Failed to summarize briefs: {str(e)}")


def summarize_briefs(client: OpenAI) -> None:
    """Summarize briefs and create embeddings."""
    try:
        briefs_dir = DATA_DIR / "brief"
        summaries_dir = DATA_DIR / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        summaries = []
        flat_summaries = []

        for file_path in briefs_dir.glob("*.txt"):
            brief_text = file_path.read_text(encoding="utf-8").strip()
            title = extract_title(brief_text)

            prompt = f"""
            Summarize the following brand brief clearly and concisely so it can be embedded later for evaluation:
            Brief:
            {brief_text}
            Respond with only the summary, no title or explanation.
            """
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
                summaries.append(
                    {"file": file_path.name, "summary": "", "error": str(e)}
                )

        # Save the summaries
        summaries_json = summaries_dir / "briefs_summaries.json"
        summaries_txt = summaries_dir / "briefs_summaries.txt"

        summaries_json.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        summaries_txt.write_text("\n\n".join(flat_summaries), encoding="utf-8")
        print(f"Saved summaries to {summaries_json} and flat text to {summaries_txt}")

    except Exception as e:
        print(f"Warning: Failed to summarize briefs: {str(e)}")


def extract_title(text: str) -> str:
    """Extract a meaningful title from the first 5 lines of the brief."""
    lines = text.strip().split("\n")[:5]
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    # Select the line with the most words
    if non_empty_lines:
        return max(non_empty_lines, key=lambda line: len(line.split()))
    return "untitled"


def initialize_vectorstore(client: OpenAI) -> None:
    """Initialize vector store with brief embeddings."""
    try:
        summaries_file = DATA_DIR / "summaries/briefs_summaries.txt"
        if not summaries_file.exists():
            print("No brief summaries found. Skipping vector store initialization.")
            return

        content = summaries_file.read_text(encoding="utf-8").strip().split("\n\n")
        if not content:
            print("No content found in summaries file.")
            return

        texts = []
        ids = []
        metadatas = []

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

        # Get embeddings
        response = client.embeddings.create(input=texts, model="text-embedding-3-small")
        embeddings = [item.embedding for item in response.data]

        # Initialize Pinecone and upsert vectors
        index = init_pinecone()
        vectors = [
            {"id": ids[i], "values": embeddings[i], "metadata": metadatas[i]}
            for i in range(len(texts))
        ]

        index.upsert(namespace="brief", vectors=vectors)
        print(f"Uploaded {len(vectors)} brief embeddings to Pinecone")

    except Exception as e:
        print(f"Warning: Failed to initialize vector store: {str(e)}")


def setup_evaluation_system() -> None:
    """Set up the complete evaluation system on first run."""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Only proceed if we have briefs
        briefs_dir = DATA_DIR / "brief"
        if not briefs_dir.exists() or not any(briefs_dir.glob("*.txt")):
            print(
                "No briefs found in data/brief/. System will use existing data if available."
            )
            return

        # Check if we need to generate summaries
        summaries_file = DATA_DIR / "summaries/briefs_summaries.txt"
        if not summaries_file.exists():
            print("Generating brief summaries...")
            asyncio.run(summarize_briefs_async(client))

        # Check if we need to generate prompts
        if not BRIEF_PROMPT_PATH.exists():
            print("Generating evaluation prompts...")
            generate_prompts(client)

        # Initialize vector store with briefs
        print("Initializing vector store...")
        initialize_vectorstore(client)

        print("Evaluation system setup complete.")

    except Exception as e:
        print(f"Warning: Setup process encountered an error: {str(e)}")
        print("The system will continue with existing data if available.")
