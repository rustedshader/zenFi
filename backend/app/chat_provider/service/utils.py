# utils.py
from langchain_chroma import Chroma


def retrieve_from_chroma(query: str, vectorstore: Chroma) -> str:
    """
    Retrieve relevant financial documents from Chroma DB with metadata.

    Args:
        query (str): Query string.
        vectorstore (Chroma): An instance of the Chroma vector store.

    Returns:
        str: A formatted string with document snippets and metadata.
    """
    docs = vectorstore.similarity_search(query, k=3)  # Get top 3 similar documents
    result = ""
    for doc in docs:
        result += (
            f"Snippet: {doc.page_content}\n"
            f"Start: {doc.metadata['start']}s\n"
            f"Duration: {doc.metadata['duration']}s\n\n"
        )
    return result.strip()
