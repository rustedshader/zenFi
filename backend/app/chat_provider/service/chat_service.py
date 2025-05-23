import datetime
from typing import AsyncGenerator
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_chroma import Chroma
from langchain.tools import Tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from pydantic import BaseModel, Field
from app.chat_provider.tools.chat_tools import ChatTools
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_community.tools import BraveSearch
from langchain_community.tools import YouTubeSearchTool
from langchain_experimental.utilities import PythonREPL
from langchain.tools import StructuredTool
from langchain_google_community import GoogleSearchAPIWrapper
from app.chat_provider.tools.stock_market_tools import StockAnalysisService
from app.chat_provider.service.chat_service_prompt import SYSTEM_PROMPT
from app.chat_provider.service.schemas import (
    State,
    WebScrapeInput,
    NoInput,
)
from app.chat_provider.service.utils import retrieve_from_google_knowledge_base
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate


class ChatService:
    def __init__(
        self,
        llm: ChatGoogleGenerativeAI,
        google_search_wrapper: GoogleSearchAPIWrapper,
        tavily_tool: TavilySearchResults,
        google_embedings: GoogleGenerativeAIEmbeddings,
        brave_search: BraveSearch.from_api_key,
    ):
        self.llm = llm
        self.search = google_search_wrapper
        self.tavily_tool = tavily_tool
        embeddings = google_embedings
        self.google_knowledge_base_tool = Tool(
            name="Google_Knowledge_Base_Search",
            func=lambda q: retrieve_from_google_knowledge_base(q),
            description="Search the Google Knowledge Base for specific financial information.",
        )

        self.yahoo_finance_tool = YahooFinanceNewsTool()
        self.python_repl = PythonREPL()

        self.google_search = Tool(
            name="google_search",
            description="Search Google for recent results.",
            func=self.search.run,
        )

        self.chat_tools = ChatTools(
            duckduckgo_general=DuckDuckGoSearchResults(),
            duckduckgo_news=DuckDuckGoSearchResults(backend="news"),
            searxng=SearxSearchWrapper(searx_host="http://localhost:8080"),
            brave_search=brave_search,
            youtube_search=YouTubeSearchTool(),
        )

        self.financial_analysis_tools = StockAnalysisService()

        self.wikipedia_tool = Tool(
            name="Wikipedia_Search",
            func=self.chat_tools.search_wikipedia,
            description="Search Wikipedia for general information.",
        )

        self.stock_price_tool = Tool(
            name="Get_Stock_Prices",
            func=self.chat_tools.get_stock_prices,
            description="Retrieve current stock prices and information for a given ticker symbol.",
        )

        self.search_web = Tool(
            name="Search_The_Internet",
            func=self.chat_tools.search_web,
            description="Search The Internet to gather information for a given query",
        )

        self.search_youtube = Tool(
            name="Search_Youtube",
            func=self.chat_tools.search_youtube,
            description="Perform comprehensive search on YouTube to get the best results and video about a given query",
        )

        self.youtube_captions_tool = Tool(
            name="Get_Youtube_Captions",
            func=self.chat_tools.get_youtube_captions,
            description="Retrieve captions and additional info for a list of YouTube video IDs. Input should be a list of video IDs (e.g., ['dQw4w9WgXcQ']).",
        )

        self.scrape_web_url = StructuredTool.from_function(
            name="Scrape_Web_URL",
            func=self.chat_tools.scrape_web_url,
            description="Retrieve data from a specific URL. Input should be a valid URL string.",
            args_schema=WebScrapeInput,
        )

        self.repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. Print values to see output.",
            func=self.python_repl.run,
        )

        self.datetime_tool = StructuredTool.from_function(
            name="Datetime",
            func=lambda: datetime.datetime.now().isoformat(),
            description="Returns the current datetime",
            args_schema=NoInput,
        )
        

        self.tools = [
            self.tavily_tool,
            self.google_knowledge_base_tool,
            self.yahoo_finance_tool,
            self.wikipedia_tool,
            self.stock_price_tool,
            self.search_web,
            self.search_youtube,
            self.repl_tool,
            self.datetime_tool,
            self.youtube_captions_tool,
            self.google_search,
            self.scrape_web_url,
        ]

        self.tool_dict = {tool.name: tool for tool in self.tools}
        self.system_prompt_message = SystemMessage(content=SYSTEM_PROMPT)

        self.state = {"messages": [self.system_prompt_message]}
        self.graph = self._build_graph()

        self.bound_llm = self.llm.bind_tools(self.tools)
    
    def load_history(self, history_dicts: list):
        """
        Replaces the current message history (except system prompt)
        with messages loaded from history_dicts (typically from DB/Redis).
        """
        self.state["messages"] = [self.system_prompt_message]
        for msg_data in history_dicts:
            sender = msg_data.get("sender")
            message_content = msg_data.get("message")
            if sender == "user":
                self.state["messages"].append(HumanMessage(content=message_content))
            elif sender == "bot":
                self.state["messages"].append(AIMessage(content=message_content))
                
    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self.chatbot)
        graph_builder.add_node("tools", self.tools_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot", self.route_tools, {"tools": "tools", END: END}
        )
        graph_builder.add_edge("tools", "chatbot")
        return graph_builder.compile()

    def chatbot(self, state: State):
        """Process messages and potentially call tools."""
        response = self.bound_llm.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(self, state: State):
        """Execute tool calls and return results, handling errors for retry."""
        last_message = state["messages"][-1]
        tool_results = []
        for tool_call in last_message.tool_calls:
            try:
                tool = self.tool_dict[tool_call["name"]]
                result = tool.invoke(tool_call["args"])
                tool_results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
            except Exception as e:
                error_message = f"Error executing tool '{tool_call['name']}': {str(e)}"
                tool_results.append(
                    ToolMessage(content=error_message, tool_call_id=tool_call["id"])
                )
        return {"messages": tool_results}

    def route_tools(self, state: State):
        """Determine if the last message has tool calls."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    def process_input(self, user_input: str):
        self.state["messages"].append(HumanMessage(content=user_input))
        final_state = self.graph.invoke(self.state)
        self.state = final_state
        last_content = self.state["messages"][-1].content
        if isinstance(last_content, list):
            last_content = "\n".join(str(item) for item in last_content)
        return last_content

    async def stream_input(self, user_input: str) -> AsyncGenerator[str, None]:
        self.state["messages"].append(HumanMessage(content=user_input))
        pointer = len(self.state["messages"])
        async for state_update in self.graph.astream(self.state, stream_mode="values"):
            self.state = state_update
            new_messages = self.state["messages"][pointer:]
            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    content = msg.content
                    if isinstance(content, list):
                        content = "\n".join(str(item) for item in content)
                    yield content
            pointer = len(self.state["messages"])
    
    def fetch_top_finance_news(self):
        """
        Uses the LLM to search across web and YouTube news channels, analyze the data,
        and return a list of the top finance news in a JSON format adhering to a specific schema.
        """

        class NewsItem(BaseModel):
            headline: str = Field(description="The headline of the news article")
            summary: str = Field(description="A short summary of the news article")
            source: str = Field(description="The source of the news article")
            publishedAt: str = Field(
                description="The publication datetime in ISO 8601 datetime string"
            )

        class NewsResponse(BaseModel):
            news: list[NewsItem] = Field(description="A list of news items")

        parser = PydanticOutputParser(pydantic_object=NewsResponse)

        prompt = PromptTemplate(
            template=(
                "Fetch the top finance news for today. "
                "Search across the web and YouTube news channels for the latest finance news. "
                "Perform an analysis of the content and provide a concise list of the best headlines along with short summaries. "
                "Return the result in pure JSON format as an object with a 'news' key that maps to an array of news items. "
                "Each news item must have the keys: 'headline', 'summary', 'source', and 'publishedAt'. "
                "Ensure that the output is valid JSON and does not include any additional text or markdown formatting.\n"
                'Ensure in this format: {{  "news": [    {{      "headline": "string",      "summary": "string",      "source": "string",      "publishedAt": "ISO 8601 datetime string"    }}  ]}}'
                "{format_instructions}"
            ),
            input_variables=[],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        prompt_and_model = prompt | self.bound_llm
        output = prompt_and_model.invoke({})

        parsed_output = parser.invoke(output)

        return parsed_output.model_dump()
