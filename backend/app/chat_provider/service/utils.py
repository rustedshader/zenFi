# utils.py
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Replace with your actual Google Knowledge Graph API key
API_KEY = os.getenv("GOOGLE_KNOWLEDGE_GRAPH_API_KEY")
ENDPOINT = "https://kgsearch.googleapis.com/v1/entities:search"


def retrieve_from_google_knowledge_base(query: str) -> str:
    """
    Retrieve relevant information from Google Knowledge Graph Search API.

    Args:
        query (str): Query string.

    Returns:
        str: A formatted string with information snippets.
    """
    # Set up API request parameters
    params = {
        "query": query,
        "limit": 3,
        "indent": True,
        "key": API_KEY,
    }

    try:
        # Make the API request
        response = requests.get(ENDPOINT, params=params)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        # Extract results from the response
        items = data.get("itemListElement", [])
        if not items:
            return "No results found."

        # Format the results
        result = ""
        for item in items:
            entity = item.get("result", {})
            name = entity.get("name", "N/A")
            description = entity.get("description", "N/A")
            detailed_description = entity.get("detailedDescription", {}).get(
                "articleBody", "N/A"
            )
            result += (
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Detailed Description: {detailed_description}\n\n"
            )
        return result.strip()

    except requests.exceptions.RequestException as e:
        return f"Error querying Google Knowledge Graph: {str(e)}"


# Example usage
if __name__ == "__main__":
    query = "Apple Inc."
    result = retrieve_from_google_knowledge_base(query)
    print(result)
