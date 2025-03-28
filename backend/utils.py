from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
)


def init_pinecone():
    """Initialize Pinecone client and ensure index exists."""
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Create index if it doesn't exist
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )

    return pc.Index(PINECONE_INDEX_NAME)


def get_embedding(text: str) -> list[float]:
    """Get OpenAI embedding for text."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    return (
        client.embeddings.create(input=[text], model="text-embedding-3-small")
        .data[0]
        .embedding
    )


def get_relevant_brief(index, submission_embedding: list[float]) -> str:
    """Query Pinecone to find the most relevant brief."""
    query_response = index.query(
        vector=submission_embedding,
        top_k=1,
        namespace="brief",
        include_metadata=True,
    )

    if not query_response.matches:
        raise ValueError("No matching brief found for submission.")

    return query_response.matches[0].metadata.get("chunk_text", "")
