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
    PriceVolumeDeliverableInput,
    IndexDataInput,
    FinancialResultsInput,
    FuturePriceVolumeInput,
    OptionPriceVolumeInput,
    LiveOptionChainInput,
    State,
    WebScrapeInput,
    NoInput,
    MFAvailableSchemesInput,
    MFQuoteInput,
    MFDetailsInput,
    MFHistoricalNAVInput,
    MFHistoryInput,
    MFBalanceUnitsValueInput,
    MFReturnsInput,
    MFPerformanceInput,
    MFAllAMCProfilesInput,
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

        self.price_volume_deliverable_tool = StructuredTool.from_function(
            func=self.chat_tools.get_price_volume_and_deliverable_data,
            name="Get_Price_Volume_Deliverable_Data",
            description="Retrieve historical price, volume, and deliverable position data for a stock.",
            args_schema=PriceVolumeDeliverableInput,
        )
        self.index_data_tool = StructuredTool.from_function(
            func=self.chat_tools.get_index_data,
            name="Get_Index_Data",
            description="Retrieve historical data for an NSE index.",
            args_schema=IndexDataInput,
        )
        self.bhav_copy_tool = Tool(
            name="Get_Bhav_Copy_With_Delivery",
            func=self.chat_tools.get_bhav_copy_with_delivery,
            description="Retrieve bhav copy with delivery data for a specific trade date (format 'dd-mm-yyyy').",
        )
        self.fno_equity_list_tool = StructuredTool.from_function(
            func=self.chat_tools.get_fno_equity_list,
            name="Get_FNO_Equity_List",
            description="Retrieve the list of derivative equities with lot sizes. No parameters required.",
            args_schema=NoInput,
        )
        self.financial_results_tool = StructuredTool.from_function(
            func=self.chat_tools.get_financial_results_for_equity,
            name="Get_Financial_Results_For_Equity",
            description="Retrieve financial results for equities.",
            args_schema=FinancialResultsInput,
        )
        self.future_price_volume_tool = StructuredTool.from_function(
            func=self.chat_tools.get_future_price_volume_data,
            name="Get_Future_Price_Volume_Data",
            description="Retrieve future price volume data for a given symbol and instrument.",
            args_schema=FuturePriceVolumeInput,
        )
        self.option_price_volume_tool = StructuredTool.from_function(
            func=self.chat_tools.get_option_price_volume_data,
            name="Get_Option_Price_Volume_Data",
            description="Retrieve option price volume data for a given symbol, instrument, and option type.",
            args_schema=OptionPriceVolumeInput,
        )
        self.fno_bhav_copy_tool = Tool(
            name="Get_FNO_Bhav_Copy",
            func=self.chat_tools.get_fno_bhav_copy,
            description="Retrieve F&O bhav copy for a specific trade date (format 'dd-mm-yyyy').",
        )
        self.participant_oi_tool = Tool(
            name="Get_Participant_Wise_Open_Interest",
            func=self.chat_tools.get_participant_wise_open_interest,
            description="Retrieve participant-wise open interest data for a specific trade date (format 'dd-mm-yyyy').",
        )
        self.participant_volume_tool = Tool(
            name="Get_Participant_Wise_Trading_Volume",
            func=self.chat_tools.get_participant_wise_trading_volume,
            description="Retrieve participant-wise trading volume data for a specific trade date (format 'dd-mm-yyyy').",
        )
        self.fii_derivatives_tool = Tool(
            name="Get_FII_Derivatives_Statistics",
            func=self.chat_tools.get_fii_derivatives_statistics,
            description="Retrieve FII derivatives statistics for a specific trade date (format 'dd-mm-yyyy').",
        )
        self.expiry_dates_future_tool = StructuredTool.from_function(
            func=self.chat_tools.get_expiry_dates_future,
            name="Get_Expiry_Dates_Future",
            description="Retrieve future and option expiry dates. No parameters required.",
            args_schema=NoInput,
        )
        self.expiry_dates_option_index_tool = StructuredTool.from_function(
            func=self.chat_tools.get_expiry_dates_option_index,
            name="Get_Expiry_Dates_Option_Index",
            description="Retrieve expiry dates for option indices. No parameters required.",
            args_schema=NoInput,
        )
        self.live_option_chain_tool = StructuredTool.from_function(
            func=self.chat_tools.get_nse_live_option_chain,
            name="Get_NSE_Live_Option_Chain",
            description="Retrieve live NSE option chain for a given symbol and expiry date.",
            args_schema=LiveOptionChainInput,
        )
        self.datetime_tool = StructuredTool.from_function(
            name="Datetime",
            func=lambda: datetime.datetime.now().isoformat(),
            description="Returns the current datetime",
            args_schema=NoInput,
        )
        self.mf_available_schemes_tool = StructuredTool.from_function(
            func=ChatTools().get_mf_available_schemes,
            name="Get_MF_Available_Schemes",
            description="Retrieve all available mutual fund schemes for a given AMC. Input: amc (str).",
            args_schema=MFAvailableSchemesInput,
        )
        self.mf_quote_tool = StructuredTool.from_function(
            func=ChatTools().get_mf_quote,
            name="Get_MF_Quote",
            description="Retrieve the latest quote for a given mutual fund scheme.",
            args_schema=MFQuoteInput,
        )
        self.mf_details_tool = StructuredTool.from_function(
            func=ChatTools().get_mf_details,
            name="Get_MF_Details",
            description="Retrieve detailed info for a given mutual fund scheme.",
            args_schema=MFDetailsInput,
        )
        self.mf_codes_tool = StructuredTool.from_function(
            func=ChatTools().get_mf_codes,
            name="Get_MF_Codes",
            description="Retrieve a dictionary of all mutual fund scheme codes and names.",
            args_schema=NoInput,
        )
        self.mf_historical_nav_tool = StructuredTool.from_function(
            func=ChatTools().get_mf_historical_nav,
            name="Get_MF_Historical_NAV",
            description="Retrieve historical NAV data for a given mutual fund scheme.",
            args_schema=MFHistoricalNAVInput,
        )
        self.mf_history_tool = StructuredTool.from_function(
            func=ChatTools().mf_history,
            name="Get_MF_History",
            description="Retrieve historical NAV data with daily changes for a mutual fund scheme.",
            args_schema=MFHistoryInput,
        )
        self.mf_balance_units_value_tool = StructuredTool.from_function(
            func=ChatTools().calculate_balance_units_value,
            name="Calculate_MF_Balance_Units_Value",
            description="Calculate the current market value of held units for a mutual fund scheme.",
            args_schema=MFBalanceUnitsValueInput,
        )
        self.mf_returns_tool = StructuredTool.from_function(
            func=ChatTools().calculate_returns,
            name="Calculate_MF_Returns",
            description="Calculate absolute and IRR annualised returns for a mutual fund scheme.",
            args_schema=MFReturnsInput,
        )
        self.mf_open_ended_equity_tool = StructuredTool.from_function(
            func=ChatTools().get_open_ended_equity_scheme_performance,
            name="Get_MF_Open_Ended_Equity_Performance",
            description="Retrieve daily performance of open ended equity mutual fund schemes.",
            args_schema=MFPerformanceInput,
        )
        self.mf_open_ended_debt_tool = StructuredTool.from_function(
            func=ChatTools().get_open_ended_debt_scheme_performance,
            name="Get_MF_Open_Ended_Debt_Performance",
            description="Retrieve daily performance of open ended debt mutual fund schemes.",
            args_schema=MFPerformanceInput,
        )
        self.mf_open_ended_hybrid_tool = StructuredTool.from_function(
            func=ChatTools().get_open_ended_hybrid_scheme_performance,
            name="Get_MF_Open_Ended_Hybrid_Performance",
            description="Retrieve daily performance of open ended hybrid mutual fund schemes.",
            args_schema=MFPerformanceInput,
        )
        self.mf_open_ended_solution_tool = StructuredTool.from_function(
            func=ChatTools().get_open_ended_solution_scheme_performance,
            name="Get_MF_Open_Ended_Solution_Performance",
            description="Retrieve daily performance of open ended solution mutual fund schemes.",
            args_schema=MFPerformanceInput,
        )
        self.mf_all_amc_profiles_tool = StructuredTool.from_function(
            func=ChatTools().get_all_amc_profiles,
            name="Get_All_MF_AMC_Profiles",
            description="Retrieve profile data of all mutual fund AMCs.",
            args_schema=MFAllAMCProfilesInput,
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
            self.price_volume_deliverable_tool,
            self.index_data_tool,
            self.bhav_copy_tool,
            self.fno_equity_list_tool,
            self.financial_results_tool,
            self.future_price_volume_tool,
            self.option_price_volume_tool,
            self.fno_bhav_copy_tool,
            self.participant_oi_tool,
            self.participant_volume_tool,
            self.fii_derivatives_tool,
            self.expiry_dates_future_tool,
            self.expiry_dates_option_index_tool,
            self.live_option_chain_tool,
            self.datetime_tool,
            self.youtube_captions_tool,
            self.google_search,
            self.mf_available_schemes_tool,
            self.mf_quote_tool,
            self.mf_details_tool,
            self.mf_codes_tool,
            self.mf_historical_nav_tool,
            self.mf_history_tool,
            self.mf_balance_units_value_tool,
            self.mf_returns_tool,
            self.mf_open_ended_equity_tool,
            self.mf_open_ended_debt_tool,
            self.mf_open_ended_hybrid_tool,
            self.mf_open_ended_solution_tool,
            self.mf_all_amc_profiles_tool,
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
