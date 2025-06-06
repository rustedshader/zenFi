from typing import List, Optional
from pydantic import BaseModel
from typing_extensions import TypedDict


class SearchQueries(BaseModel):
    queries: Optional[List[str]]


class FinanceNews(BaseModel):
    topic: Optional[str]
    description: Optional[str]
    content: Optional[str]
    sources: Optional[List[str]]
    summary: Optional[str]


# Add this new model to wrap multiple FinanceNews objects
class FinanceNewsReport(BaseModel):
    news_items: List[FinanceNews]


class FinanceNewsState(TypedDict):
    topic: Optional[List[str]]
    messages: Optional[List[str]]
    search_queries: Optional[List[str]]
    search_response: Optional[str]
    news_search_queries: Optional[List[str]]
    news_search_response: Optional[str]
    news_report: Optional[List[FinanceNews]]
