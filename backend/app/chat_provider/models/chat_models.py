from typing import Annotated, List, TypedDict, Literal, Optional
from pydantic import BaseModel, Field
import operator
from langgraph.graph.message import add_messages


# Updated AppState with 'code' field
class AppState(TypedDict):
    messages: Annotated[list, add_messages]
    needs_portfolio: Optional[bool]
    needs_knowledge_base: Optional[bool]
    search_queries: list[str]
    search_sufficient: Optional[bool]
    summary: Optional[str]
    needs_python_code: Optional[bool]
    code: Optional[str]
