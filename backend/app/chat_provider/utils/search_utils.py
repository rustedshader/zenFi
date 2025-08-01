import os
import asyncio
import requests
import random
import concurrent
import aiohttp
import httpx
import time
from typing import List, Optional, Dict, Any, Union, Literal
from urllib.parse import unquote
from tavily import AsyncTavilyClient
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from markdownify import markdownify
from langchain_core.tools import tool

from langsmith import traceable

from app.chat_provider.models.deepsearch_models import Section


def get_config_value(value):
    """
    Helper function to handle string, dict, and enum cases of configuration values
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        return value
    else:
        return value.value


def get_search_params(
    search_api: str, search_api_config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Filters the search_api_config dictionary to include only parameters accepted by the specified search API.

    Args:
        search_api (str): The search API identifier (e.g., "exa", "tavily").
        search_api_config (Optional[Dict[str, Any]]): The configuration dictionary for the search API.

    Returns:
        Dict[str, Any]: A dictionary of parameters to pass to the search function.
    """
    # Define accepted parameters for each search API
    SEARCH_API_PARAMS = {
        "exa": [
            "max_characters",
            "num_results",
            "include_domains",
            "exclude_domains",
            "subpages",
        ],
        "tavily": ["max_results", "topic"],
        "perplexity": [],  # Perplexity accepts no additional parameters
        "linkup": ["depth"],
        "googlesearch": ["max_results"],
    }

    # Get the list of accepted parameters for the given search API
    accepted_params = SEARCH_API_PARAMS.get(search_api, [])

    # If no config provided, return an empty dict
    if not search_api_config:
        return {}

    # Filter the config to only include accepted parameters
    return {k: v for k, v in search_api_config.items() if k in accepted_params}


def deduplicate_and_format_sources(
    search_response, max_tokens_per_source=5000, include_raw_content=True
):
    """
    Takes a list of search responses and formats them into a readable string.
    Limits the raw_content to approximately max_tokens_per_source tokens.

    Args:
        search_responses: List of search response dicts, each containing:
            - query: str
            - results: List of dicts with fields:
                - title: str
                - url: str
                - content: str
                - score: float
                - raw_content: str|None
        max_tokens_per_source: int
        include_raw_content: bool

    Returns:
        str: Formatted string with deduplicated sources
    """
    # Collect all results
    sources_list = []
    for response in search_response:
        sources_list.extend(response["results"])

    # Deduplicate by URL
    unique_sources = {source["url"]: source for source in sources_list}

    # Format output
    formatted_text = "Content from sources:\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"{'=' * 80}\n"  # Clear section separator
        formatted_text += f"Source: {source['title']}\n"
        formatted_text += f"{'-' * 80}\n"  # Subsection separator
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += (
            f"Most relevant content from source: {source['content']}\n===\n"
        )
        if include_raw_content:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get("raw_content", "")
            if raw_content is None:
                raw_content = ""
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
        formatted_text += f"{'=' * 80}\n\n"  # End section separator

    return formatted_text.strip()


def format_sections(sections: list[Section]) -> str:
    """Format a list of sections into a string"""
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{"=" * 60}
Section {idx}: {section.name}
{"=" * 60}
Description:
{section.description}
Requires Research: 
{section.research}

Content:
{section.content if section.content else "[Not yet written]"}

"""
    return formatted_str


@traceable
async def tavily_search_async(
    search_queries,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
):
    """
    Performs concurrent web searches with the Tavily API

    Args:
        search_queries (List[str]): List of search queries to process
        max_results (int): Maximum number of results to return
        topic (Literal["general", "news", "finance"]): Topic to filter results by
        include_raw_content (bool): Whether to include raw content in the results

    Returns:
            List[dict]: List of search responses from Tavily API:
                {
                    'query': str,
                    'follow_up_questions': None,
                    'answer': None,
                    'images': list,
                    'results': [                     # List of search results
                        {
                            'title': str,            # Title of the webpage
                            'url': str,              # URL of the result
                            'content': str,          # Summary/snippet of content
                            'score': float,          # Relevance score
                            'raw_content': str|None  # Full page content if available
                        },
                        ...
                    ]
                }
    """
    tavily_async_client = AsyncTavilyClient()
    search_tasks = []
    for query in search_queries:
        search_tasks.append(
            tavily_async_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
        )

    # Execute all searches concurrently
    search_docs = await asyncio.gather(*search_tasks)
    return search_docs


@traceable
async def google_search_async(
    search_queries: Union[str, List[str]],
    max_results: int = 5,
    include_raw_content: bool = True,
):
    """
    Performs concurrent web searches using Google.
    Uses Google Custom Search API if environment variables are set, otherwise falls back to web scraping.

    Args:
        search_queries (List[str]): List of search queries to process
        max_results (int): Maximum number of results to return per query
        include_raw_content (bool): Whether to fetch full page content

    Returns:
        List[dict]: List of search responses from Google, one per query
    """

    # Check for API credentials from environment variables
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("GOOGLE_CX")
    use_api = bool(api_key and cx)

    # Handle case where search_queries is a single string
    if isinstance(search_queries, str):
        search_queries = [search_queries]

    # Define user agent generator
    def get_useragent():
        """Generates a random user agent string."""
        lynx_version = (
            f"Lynx/{random.randint(2, 3)}.{random.randint(8, 9)}.{random.randint(0, 2)}"
        )
        libwww_version = f"libwww-FM/{random.randint(2, 3)}.{random.randint(13, 15)}"
        ssl_mm_version = f"SSL-MM/{random.randint(1, 2)}.{random.randint(3, 5)}"
        openssl_version = f"OpenSSL/{random.randint(1, 3)}.{random.randint(0, 4)}.{random.randint(0, 9)}"
        return f"{lynx_version} {libwww_version} {ssl_mm_version} {openssl_version}"

    # Create executor for running synchronous operations
    executor = None if use_api else concurrent.futures.ThreadPoolExecutor(max_workers=5)

    # Use a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(5 if use_api else 2)

    async def search_single_query(query):
        async with semaphore:
            try:
                results = []

                # API-based search
                if use_api:
                    # The API returns up to 10 results per request
                    for start_index in range(1, max_results + 1, 10):
                        # Calculate how many results to request in this batch
                        num = min(10, max_results - (start_index - 1))

                        # Make request to Google Custom Search API
                        params = {
                            "q": query,
                            "key": api_key,
                            "cx": cx,
                            "start": start_index,
                            "num": num,
                        }
                        print(
                            f"Requesting {num} results for '{query}' from Google API..."
                        )

                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                "https://www.googleapis.com/customsearch/v1",
                                params=params,
                            ) as response:
                                if response.status != 200:
                                    error_text = await response.text()
                                    print(f"API error: {response.status}, {error_text}")
                                    break

                                data = await response.json()

                                # Process search results
                                for item in data.get("items", []):
                                    print(
                                        f"Title: {item.get('title')} Link: {item.get('link')}"
                                    )
                                    result = {
                                        "title": item.get("title", ""),
                                        "url": item.get("link", ""),
                                        "content": item.get("snippet", ""),
                                        "score": None,
                                        "raw_content": item.get("snippet", ""),
                                    }
                                    results.append(result)

                        # Respect API quota with a small delay
                        await asyncio.sleep(0.2)

                        # If we didn't get a full page of results, no need to request more
                        if not data.get("items") or len(data.get("items", [])) < num:
                            break

                # Web scraping based search
                else:
                    # Add delay between requests
                    await asyncio.sleep(0.5 + random.random() * 1.5)
                    print(f"Scraping Google for '{query}'...")

                    # Define scraping function
                    def google_search(query, max_results):
                        try:
                            lang = "en"
                            safe = "active"
                            start = 0
                            fetched_results = 0
                            fetched_links = set()
                            search_results = []

                            while fetched_results < max_results:
                                # Send request to Google
                                resp = requests.get(
                                    url="https://www.google.com/search",
                                    headers={
                                        "User-Agent": get_useragent(),
                                        "Accept": "*/*",
                                    },
                                    params={
                                        "q": query,
                                        "num": max_results + 2,
                                        "hl": lang,
                                        "start": start,
                                        "safe": safe,
                                    },
                                    cookies={
                                        "CONSENT": "PENDING+987",  # Bypasses the consent page
                                        "SOCS": "CAESHAgBEhIaAB",
                                    },
                                )
                                resp.raise_for_status()

                                # Parse results
                                soup = BeautifulSoup(resp.text, "html.parser")
                                result_block = soup.find_all("div", class_="ezO2md")
                                new_results = 0

                                for result in result_block:
                                    link_tag = result.find("a", href=True)
                                    title_tag = (
                                        link_tag.find("span", class_="CVA68e")
                                        if link_tag
                                        else None
                                    )
                                    description_tag = result.find(
                                        "span", class_="FrIlee"
                                    )

                                    if link_tag and title_tag and description_tag:
                                        link = unquote(
                                            link_tag["href"]
                                            .split("&")[0]
                                            .replace("/url?q=", "")
                                        )

                                        if link in fetched_links:
                                            continue

                                        fetched_links.add(link)
                                        title = title_tag.text
                                        description = description_tag.text

                                        # Store result in the same format as the API results
                                        search_results.append(
                                            {
                                                "title": title,
                                                "url": link,
                                                "content": description,
                                                "score": None,
                                                "raw_content": description,
                                            }
                                        )

                                        fetched_results += 1
                                        new_results += 1

                                        if fetched_results >= max_results:
                                            break

                                if new_results == 0:
                                    break

                                start += 10
                                time.sleep(1)  # Delay between pages

                            return search_results

                        except Exception as e:
                            print(f"Error in Google search for '{query}': {str(e)}")
                            return []

                    # Execute search in thread pool
                    loop = asyncio.get_running_loop()
                    search_results = await loop.run_in_executor(
                        executor, lambda: google_search(query, max_results)
                    )

                    # Process the results
                    results = search_results

                # If requested, fetch full page content asynchronously (for both API and web scraping)
                if include_raw_content and results:
                    content_semaphore = asyncio.Semaphore(3)

                    async with aiohttp.ClientSession() as session:
                        fetch_tasks = []

                        async def fetch_full_content(result):
                            async with content_semaphore:
                                url = result["url"]
                                headers = {
                                    "User-Agent": get_useragent(),
                                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                }

                                try:
                                    await asyncio.sleep(0.2 + random.random() * 0.6)
                                    async with session.get(
                                        url, headers=headers, timeout=10
                                    ) as response:
                                        if response.status == 200:
                                            # Check content type to handle binary files
                                            content_type = response.headers.get(
                                                "Content-Type", ""
                                            ).lower()

                                            # Handle PDFs and other binary files
                                            if (
                                                "application/pdf" in content_type
                                                or "application/octet-stream"
                                                in content_type
                                            ):
                                                # For PDFs, indicate that content is binary and not parsed
                                                result["raw_content"] = (
                                                    f"[Binary content: {content_type}. Content extraction not supported for this file type.]"
                                                )
                                            else:
                                                try:
                                                    # Try to decode as UTF-8 with replacements for non-UTF8 characters
                                                    html = await response.text(
                                                        errors="replace"
                                                    )
                                                    soup = BeautifulSoup(
                                                        html, "html.parser"
                                                    )
                                                    result["raw_content"] = (
                                                        soup.get_text()
                                                    )
                                                except UnicodeDecodeError as ude:
                                                    # Fallback if we still have decoding issues
                                                    result["raw_content"] = (
                                                        f"[Could not decode content: {str(ude)}]"
                                                    )
                                except Exception as e:
                                    print(
                                        f"Warning: Failed to fetch content for {url}: {str(e)}"
                                    )
                                    result["raw_content"] = (
                                        f"[Error fetching content: {str(e)}]"
                                    )
                                return result

                        for result in results:
                            fetch_tasks.append(fetch_full_content(result))

                        updated_results = await asyncio.gather(*fetch_tasks)
                        results = updated_results
                        print(f"Fetched full content for {len(results)} results")

                return {
                    "query": query,
                    "follow_up_questions": None,
                    "answer": None,
                    "images": [],
                    "results": results,
                }
            except Exception as e:
                print(f"Error in Google search for query '{query}': {str(e)}")
                return {
                    "query": query,
                    "follow_up_questions": None,
                    "answer": None,
                    "images": [],
                    "results": [],
                }

    try:
        # Create tasks for all search queries
        search_tasks = [search_single_query(query) for query in search_queries]

        # Execute all searches concurrently
        search_results = await asyncio.gather(*search_tasks)

        return search_results
    finally:
        # Only shut down executor if it was created
        if executor:
            executor.shutdown(wait=False)


async def scrape_pages(titles: List[str], urls: List[str]) -> str:
    """
    Scrapes content from a list of URLs and formats it into a readable markdown document.

    This function:
    1. Takes a list of page titles and URLs
    2. Makes asynchronous HTTP requests to each URL
    3. Converts HTML content to markdown
    4. Formats all content with clear source attribution

    Args:
        titles (List[str]): A list of page titles corresponding to each URL
        urls (List[str]): A list of URLs to scrape content from

    Returns:
        str: A formatted string containing the full content of each page in markdown format,
             with clear section dividers and source attribution
    """

    # Create an async HTTP client
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        pages = []

        # Fetch each URL and convert to markdown
        for url in urls:
            try:
                # Fetch the content
                response = await client.get(url)
                response.raise_for_status()

                # Convert HTML to markdown if successful
                if response.status_code == 200:
                    # Handle different content types
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        # Convert HTML to markdown
                        markdown_content = markdownify(response.text)
                        pages.append(markdown_content)
                    else:
                        # For non-HTML content, just mention the content type
                        pages.append(
                            f"Content type: {content_type} (not converted to markdown)"
                        )
                else:
                    pages.append(f"Error: Received status code {response.status_code}")

            except Exception as e:
                # Handle any exceptions during fetch
                pages.append(f"Error fetching URL: {str(e)}")

        # Create formatted output
        formatted_output = "Search results: \n\n"

        for i, (title, url, page) in enumerate(zip(titles, urls, pages)):
            formatted_output += f"\n\n--- SOURCE {i + 1}: {title} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += f"FULL CONTENT:\n {page}"
            formatted_output += "\n\n" + "-" * 80 + "\n"

    return formatted_output


@tool
async def duckduckgo_search(search_queries: List[str]):
    """Perform searches using DuckDuckGo with retry logic to handle rate limits

    Args:
        search_queries (List[str]): List of search queries to process

    Returns:
        List[dict]: List of search results
    """

    async def process_single_query(query):
        # Execute synchronous search in the event loop's thread pool
        loop = asyncio.get_event_loop()

        def perform_search():
            max_retries = 3
            retry_count = 0
            backoff_factor = 2.0
            last_exception = None

            while retry_count <= max_retries:
                try:
                    results = []
                    with DDGS() as ddgs:
                        # Change query slightly and add delay between retries
                        if retry_count > 0:
                            # Random delay with exponential backoff
                            delay = backoff_factor**retry_count + random.random()
                            print(
                                f"Retry {retry_count}/{max_retries} for query '{query}' after {delay:.2f}s delay"
                            )
                            time.sleep(delay)

                            # Add a random element to the query to bypass caching/rate limits
                            modifiers = [
                                "about",
                                "info",
                                "guide",
                                "overview",
                                "details",
                                "explained",
                            ]
                            modified_query = f"{query} {random.choice(modifiers)}"
                        else:
                            modified_query = query

                        # Execute search
                        ddg_results = list(ddgs.text(modified_query, max_results=5))

                        # Format results
                        for i, result in enumerate(ddg_results):
                            results.append(
                                {
                                    "title": result.get("title", ""),
                                    "url": result.get("href", ""),
                                    "content": result.get("body", ""),
                                    "score": 1.0
                                    - (i * 0.1),  # Simple scoring mechanism
                                    "raw_content": result.get("body", ""),
                                }
                            )

                        # Return successful results
                        return {
                            "query": query,
                            "follow_up_questions": None,
                            "answer": None,
                            "images": [],
                            "results": results,
                        }
                except Exception as e:
                    # Store the exception and retry
                    last_exception = e
                    retry_count += 1
                    print(
                        f"DuckDuckGo search error: {str(e)}. Retrying {retry_count}/{max_retries}"
                    )

                    # If not a rate limit error, don't retry
                    if "Ratelimit" not in str(e) and retry_count >= 1:
                        print(f"Non-rate limit error, stopping retries: {str(e)}")
                        break

            # If we reach here, all retries failed
            print(f"All retries failed for query '{query}': {str(last_exception)}")
            # Return empty results but with query info preserved
            return {
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": [],
                "error": str(last_exception),
            }

        return await loop.run_in_executor(None, perform_search)

    # Process queries with delay between them to reduce rate limiting
    search_docs = []
    urls = []
    titles = []
    for i, query in enumerate(search_queries):
        # Add delay between queries (except first one)
        if i > 0:
            delay = 2.0 + random.random() * 2.0  # Random delay 2-4 seconds
            await asyncio.sleep(delay)

        # Process the query
        result = await process_single_query(query)
        search_docs.append(result)

        # Safely extract URLs and titles from results, handling empty result cases
        if result["results"] and len(result["results"]) > 0:
            for res in result["results"]:
                if "url" in res and "title" in res:
                    urls.append(res["url"])
                    titles.append(res["title"])

    # If we got any valid URLs, scrape the pages
    if urls:
        return await scrape_pages(titles, urls)
    else:
        # Return a formatted error message if no valid URLs were found
        return "No valid search results found. Please try different search queries or use a different search API."


@tool
async def tavily_search(
    queries: List[str],
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> str:
    """
    Fetches results from Tavily search API.

    Args:
        queries (List[str]): List of search queries
        max_results (int): Maximum number of results to return
        topic (Literal["general", "news", "finance"]): Topic to filter results by

    Returns:
        str: A formatted string of search results
    """
    # Use tavily_search_async with include_raw_content=True to get content directly
    search_results = await tavily_search_async(
        queries, max_results=5, topic="general", include_raw_content=True
    )

    # Format the search results directly using the raw_content already provided
    formatted_output = f"Search results: \n\n"

    # Deduplicate results by URL
    unique_results = {}
    for response in search_results:
        for result in response["results"]:
            url = result["url"]
            if url not in unique_results:
                unique_results[url] = result

    # Format the unique results
    for i, (url, result) in enumerate(unique_results.items()):
        formatted_output += f"\n\n--- SOURCE {i + 1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        if result.get("raw_content"):
            formatted_output += (
                f"FULL CONTENT:\n{result['raw_content'][:30000]}"  # Limit content size
            )
        formatted_output += "\n\n" + "-" * 80 + "\n"

    if unique_results:
        return formatted_output
    else:
        return "No valid search results found. Please try different search queries or use a different search API."


async def select_and_execute_search(
    search_api: str, query_list: list[str], params_to_pass: dict
) -> str:
    """Select and execute the appropriate search API.

    Args:
        search_api: Name of the search API to use
        query_list: List of search queries to execute
        params_to_pass: Parameters to pass to the search API

    Returns:
        Formatted string containing search results

    Raises:
        ValueError: If an unsupported search API is specified
    """
    print(f"query_list: {query_list} params_to_pass: {params_to_pass}")
    if search_api == "tavily":
        # Tavily search tool used with both workflow and agent
        return await tavily_search.ainvoke({"queries": query_list}, **params_to_pass)
    elif search_api == "duckduckgo":
        # DuckDuckGo search tool used with both workflow and agent
        return await duckduckgo_search.ainvoke({"search_queries": query_list})
    elif search_api == "googlesearch":
        search_results = await google_search_async(query_list, **params_to_pass)
        return deduplicate_and_format_sources(
            search_results, max_tokens_per_source=4000
        )
    else:
        raise ValueError(f"Unsupported search API: {search_api}")
