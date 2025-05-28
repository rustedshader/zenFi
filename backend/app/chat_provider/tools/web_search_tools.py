import os
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool
from dotenv import load_dotenv
from langchain_community.tools import (
    BraveSearch,
    DuckDuckGoSearchRun,
    DuckDuckGoSearchResults,
)


load_dotenv()

google_cse_id = os.environ["GOOGLE_SEARCH_CSE_ID"]
google_api_key = os.environ["GOOGLE_SEARCH_API_KEY"]
brave_search_api_key = os.environ["BRAVE_SEARCH_API_KEY"]

search = GoogleSearchAPIWrapper(
    k=10, google_cse_id=google_cse_id, google_api_key=google_api_key
)

# tool name: google_search
google_search_tool = Tool(
    name="google_search",
    description="Search Google for recent results.",
    func=search.run,
)

# tool name: brave_search
brave_search_tool = BraveSearch.from_api_key(
    api_key=brave_search_api_key, search_kwargs={"count": 5}
)

# tool name: duckduckgo_search
duckduckgo_search_run_tool = DuckDuckGoSearchRun()

# tool name: duckduckgo_results_json
duckduckgo_search_results_tool = DuckDuckGoSearchResults()


# TODO: Complete These Searches
def searxng_search(input_query: str):
    pass


def perplexity_search(input_query: str):
    pass


def tavily_search(input_query: str):
    pass


def complete_web_search(input_query: str):
    pass


if __name__ == "__main__":
    print(google_api_key, google_cse_id)
