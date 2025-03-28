from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
)
from fastapi import HTTPException


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
