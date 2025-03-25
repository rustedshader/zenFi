import datetime
from typing import Annotated, AsyncGenerator
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_chroma import Chroma
from langchain.tools import Tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.yahoo_finance_news import (
    YahooFinanceNewsTool,
)
from app.chat_provider.tools.chat_tools import ChatTools
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_community.tools import BraveSearch
from langchain_community.tools import YouTubeSearchTool
from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.messages import AIMessage


"""
TOADD:

Added IF Date is given then its of year 2025 you don't have to search of past.

If user is asking for best stocks to invest in parse todays date too.

In indian stocks add .NS in end

Implement advanced calculations to predict stocks prices. Use advanced finance math

Add Youtube Finance News Channel Transcript To DB

"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


class PriceVolumeDeliverableInput(BaseModel):
    symbol: str = Field(..., description="The stock symbol, e.g., 'RELIANCE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '15D', optional")


# Schema for index_data_tool
class IndexDataInput(BaseModel):
    index: str = Field(..., description="The NSE index, e.g., 'NIFTY 50'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


# Schema for financial_results_tool
class FinancialResultsInput(BaseModel):
    symbol: str = Field(..., description="The stock symbol, e.g., 'RELIANCE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")
    fo_sec: bool = Field(None, description="F&O security flag, optional")
    fin_period: str = Field(
        "Quarterly", description="Financial period, e.g., 'Quarterly', optional"
    )


# Schema for future_price_volume_tool
class FuturePriceVolumeInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'BANKNIFTY'")
    instrument: str = Field(..., description="Instrument type, 'FUTIDX' or 'FUTSTK'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


# Schema for option_price_volume_tool
class OptionPriceVolumeInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'NIFTY'")
    instrument: str = Field(..., description="Instrument type, 'OPTIDX' or 'OPTSTK'")
    option_type: str = Field(..., description="Option type, 'PE' or 'CE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


# Schema for live_option_chain_tool
class LiveOptionChainInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'BANKNIFTY'")
    expiry_date: str = Field(
        None, description="Expiry date in 'dd-mm-yyyy' format, optional"
    )
    oi_mode: str = Field(
        "full", description="Open interest mode, 'full' or 'compact', optional"
    )


class NoInput(BaseModel):
    pass


# Custom function to query Chroma DB
def retrieve_from_chroma(query: str, vectorstore: Chroma):
    """Retrieve relevant financial documents from Chroma DB with metadata."""
    docs = vectorstore.similarity_search(query, k=3)  # Get top 3 similar documents
    result = ""
    for doc in docs:
        result += f"Snippet: {doc.page_content}\nStart: {doc.metadata['start']}s\nDuration: {doc.metadata['duration']}s\n\n"
    return result.strip()


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

        # Initialize existing tools
        self.tavily_tool = tavily_tool
        embeddings = google_embedings
        self.vectorstore = Chroma(
            persist_directory="knowledge_base_db",
            embedding_function=embeddings,
        )
        self.chroma_tool = Tool(
            name="Chroma_DB_Search",
            func=lambda q: retrieve_from_chroma(q, self.vectorstore),
            description="Search the Chroma database for specific financial information.",
        )
        self.yahoo_finance_tool = YahooFinanceNewsTool()

        self.python_repl = PythonREPL()

        self.google_search = Tool(
            name="google_search",
            description="Search Google for recent results.",
            func=self.search.run,
        )

        # Initialize ChatTools with multiple search tools
        self.chat_tools = ChatTools(
            duckduckgo_general=DuckDuckGoSearchResults(),
            duckduckgo_news=DuckDuckGoSearchResults(backend="news"),
            searxng=SearxSearchWrapper(searx_host="http://localhost:8080"),
            brave_search=brave_search,
            youtube_search=YouTubeSearchTool(),
        )

        # Define additional tools using ChatTools methods
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

        # New comprehensive web search tool for financial research
        self.web_financial_research_tool = Tool(
            name="Web_Financial_Research",
            func=self.comprehensive_stock_research,
            description="Perform comprehensive web-based research on a stock, including company info, news, financial analysis, and market insights.",
        )
        self.search_youtube = Tool(
            name="Search_Youtube",
            func=self.chat_tools.search_youtube,
            description="Perform comprehesive search on youtube to get the best results and video about given query",
        )

        self.youtube_captions_tool = Tool(
            name="Get_Youtube_Captions",
            func=self.chat_tools.get_youtube_captions,
            description="Retrieve captions and additional info for a list of YouTube video IDs. Input should be a list of video IDs (e.g., ['dQw4w9WgXcQ']).",
        )

        self.repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=self.python_repl.run,
        )

        self.price_volume_deliverable_tool = StructuredTool.from_function(
            func=self.chat_tools.get_price_volume_and_deliverable_data,
            name="Get_Price_Volume_Deliverable_Data",
            description="Retrieve historical price, volume, and deliverable position data for a stock. Use this tool to analyze stock performance over time.",
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
            description="Retrieve bhav copy with delivery data for a specific trade date. Parameters: trade_date (str, 'dd-mm-yyyy').",
        )
        self.equity_list_tool = StructuredTool.from_function(
            func=self.chat_tools.get_equity_list,
            name="Get_Equity_List",
            description="Retrieve the list of all equities available to trade on NSE. No parameters required.",
            args_schema=NoInput,
        )
        self.fno_equity_list_tool = StructuredTool.from_function(
            func=self.chat_tools.get_fno_equity_list,
            name="Get_FNO_Equity_List",
            description="Retrieve the list of derivative equities with lot sizes. No parameters required.",
            args_schema=NoInput,
        )
        self.market_watch_tool = StructuredTool.from_function(
            func=self.chat_tools.get_market_watch_all_indices,
            name="Get_Market_Watch_All_Indices",
            description="Retrieve market watch data for all NSE indices. No parameters required.",
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
            description="Retrieve F&O bhav copy for a specific trade date. Parameter: trade_date (str, 'dd-mm-yyyy', e.g., '20-06-2023').",
        )
        self.participant_oi_tool = Tool(
            name="Get_Participant_Wise_Open_Interest",
            func=self.chat_tools.get_participant_wise_open_interest,
            description="Retrieve participant-wise open interest data (FII, DII, etc.) for a specific trade date. Parameter: trade_date (str, 'dd-mm-yyyy', e.g., '20-06-2023').",
        )
        self.participant_volume_tool = Tool(
            name="Get_Participant_Wise_Trading_Volume",
            func=self.chat_tools.get_participant_wise_trading_volume,
            description="Retrieve participant-wise trading volume data for a specific trade date. Parameter: trade_date (str, 'dd-mm-yyyy', e.g., '20-06-2023').",
        )
        self.fii_derivatives_tool = Tool(
            name="Get_FII_Derivatives_Statistics",
            func=self.chat_tools.get_fii_derivatives_statistics,
            description="Retrieve FII derivatives statistics for a specific trade date. Parameter: trade_date (str, 'dd-mm-yyyy', e.g., '20-06-2023').",
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

        # Combine all tools into the tools list
        self.tools = [
            self.tavily_tool,
            self.chroma_tool,
            self.yahoo_finance_tool,
            self.wikipedia_tool,
            self.stock_price_tool,
            self.search_web,
            self.web_financial_research_tool,
            self.search_youtube,
            self.repl_tool,
            self.price_volume_deliverable_tool,
            self.index_data_tool,
            self.bhav_copy_tool,
            self.equity_list_tool,
            self.fno_equity_list_tool,
            self.market_watch_tool,
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
        ]

        # Initialize state with system message (using the previous system message)
        self.state = {
            "messages": [
                SystemMessage(
                    content="""You are an advanced GenAI financial assistant designed specifically for Indian investors. Your primary mission is to democratize financial knowledge and empower millions of emerging investors through accessible, personalized guidance.

**Key Responsibilities:**
- Provide clear, jargon-free explanations of financial concepts
- Introduce and explain various Indian investment products
- Help users understand their risk profiles
- Guide users through informed investment decision-making
- Promote financial literacy and long-term wealth creation
- Assist users in choosing the best stocks in the market
- Use advanced mathematical calculations to predict trends and provide insightful financial advice
- If you explained a topic ask and suggest user more topics that he wants to learn.
- Try to explain by giving easy to understand refrences.

**Communication Guidelines:**
- Use simple, relatable language
- Adapt to the user's financial literacy level
- Be patient, supportive, and encouraging
- Prioritize education alongside investment advice
- Provide financial advice but always include a warning about inherent risks
- Always provide YouTube video links when users want to learn or inquire about any topic

**Investment Product Focus:**
- Mutual Funds
- Stock Market Investments
- Government Securities
- Fixed Deposits
- Public Provident Fund (PPF)
- National Pension System (NPS)
- Systematic Investment Plans (SIPs)

**Ethical Principles:**
- Always recommend consulting professional financial advisors
- Emphasize the importance of personal research
- Highlight potential risks and returns
- Maintain complete transparency about being an AI advisor

**Tool Usage:**
- Use *Datetime* to get the current Date and Time. 
- Use *Yahoo Finance* to fetch recent news articles for specific stock tickers by providing the ticker as a 'query' parameter (e.g., call it with {"query": "RELIANCE.NS"}). For Indian stocks, append ".NS" for NSE or ".BO" for BSE (e.g., "RELIANCE.NS" for Reliance Industries on NSE).
- Use *Chroma_DB_Search* to retrieve relevant information from financial news video transcripts by providing a query string (e.g., {"query": "Indian stock market trends"}).
- Use *Get_Stock_Prices* to fetch current stock prices by providing the ticker as a single string (e.g., "SBIN.NS"). Append '.NS' for Indian stocks. You can get Realtime stock data using it.
- Use *Web_Financial_Research* for comprehensive stock research across multiple sources by providing a query string (e.g., {"query": "TCS stock analysis"}).
- Use *google_search* for searching web and getting web results. Run *Search_The_Internet* too when running this to gather as much data.
- Use *Search_The_Internet* for general web searches to gather financial data, news, or advice about a company, verify doubtful information, or get the latest updates by providing a query string (e.g., {"query": "latest RBI monetary policy"}). Use Tavily with it to get best web search results. 
- Use *Search_Youtube* when users want to learn about financial terms or topics, providing video links by searching with a query string (e.g., {"query": "how to invest in mutual funds India"}). Also provide links if users specifically request them.
- Use *python_repl* for mathematical calculations by providing Python code as a string (e.g., "import pandas as pd; data = [100, 110, 105]; pd.Series(data).mean()"). Parse Python code to apply financial formulas and analyze stock data for better advice. Never give code in the output. Perform and execute the python code and display result.
- Use *Wikipedia_Search* to search Wikipedia. Always try to use it for verifying facts and informations. If you have ever trouble finding correct company alias you can refer to this wikepdia page List_of_companies_listed_on_the_National_Stock_Exchange_of_India 
- Use *Get_Youtube_Captions* to get captions/subtitles of a youtube video. Schema You have to parse is list of strings of youtube ids ["xyz","abc"]

Please execute the following steps and provide the final output. Do not just list the steps; actually perform the calculations and actions required


**NSE Data Tools for Financial Analysis:**
- *Get_Price_Volume_Deliverable_Data*: Fetch historical price, volume, and deliverable data for a stock. Parameters: symbol (e.g., "SBIN"), from_date, to_date, period (e.g., "1M"). Example call: {"symbol": "SBIN", "period": "1M"}.
- *Get_Index_Data*: Retrieve historical data on NSE indices like NIFTY 50. Parameters: index (e.g., "NIFTY 50"), from_date, to_date, period. Example call: {"index": "NIFTY 50", "period": "6M"}.
- *Get_Bhav_Copy_With_Delivery*: Get daily market data, including delivery details, for a specific trade date. Parameter: trade_date (e.g., "15-08-2023"). Example call: {"trade_date": "15-08-2023"}.
- *Get_Equity_List*: Provide a list of all equities available on NSE. No parameters needed. Example call: {}.
- *Get_FNO_Equity_List*: Fetch derivative equities with lot sizes. No parameters needed. Example call: {}.
- *Get_Market_Watch_All_Indices*: Obtain current market data for all NSE indices. No parameters needed. Example call: {}.
- *Get_Financial_Results_For_Equity*: Retrieve financial results for equities. Parameters: from_date, to_date, period, fo_sec (boolean), fin_period (e.g., "Quarterly"). Example call: {"symbol": "RELIANCE", "fin_period": "Quarterly"}.
- *Get_Future_Price_Volume_Data*: Access historical futures price and volume data for a stock or index. Parameters: symbol (e.g., "BANKNIFTY"), instrument ("FUTIDX" or "FUTSTK"), from_date, to_date, period. Example call: {"symbol": "BANKNIFTY", "instrument": "FUTIDX", "period": "1M"}.
- *Get_Option_Price_Volume_Data*: Fetch historical options price and volume data. Parameters: symbol (e.g., "NIFTY"), instrument ("OPTIDX" or "OPTSTK"), option_type ("PE" or "CE"), from_date, to_date, period. Example call: {"symbol": "NIFTY", "instrument": "OPTIDX", "option_type": "CE", "period": "1M"}.
- *Get_FNO_Bhav_Copy*: Retrieve F&O bhav copy for a specific trade date. Parameter: trade_date (e.g., "20-06-2023"). Example call: {"trade_date": "20-06-2023"}.
- *Get_Participant_Wise_Open_Interest*: Get open interest data by participant type (FII, DII, etc.). Parameter: trade_date (e.g., "20-06-2023"). Example call: {"trade_date": "20-06-2023"}.
- *Get_Participant_Wise_Trading_Volume*: Fetch trading volume data by participant type. Parameter: trade_date (e.g., "20-06-2023"). Example call: {"trade_date": "20-06-2023"}.
- *Get_FII_Derivatives_Statistics*: Access FII derivatives trading statistics. Parameter: trade_date (e.g., "20-06-2023"). Example call: {"trade_date": "20-06-2023"}.
- *Get_Expiry_Dates_Future*: Retrieve future expiry dates. No parameters needed. Example call: {}.
- *Get_NSE_Live_Option_Chain*: Fetch live option chain data. Parameters: symbol (e.g., "BANKNIFTY"), expiry_date (optional), oi_mode ("full" or "compact"). Example call: {"symbol": "BANKNIFTY", "oi_mode": "full"}.

Please execute the following steps and provide the final output. Do not just list the steps; actually perform the calculations and actions required

**Important Notes for NSE Data Usage:**
- For NSE-specific tools, use stock symbols without suffixes (e.g., "SBIN").
- For tools like *Get_Stock_Prices* and *Yahoo Finance*, append ".NS" for NSE stocks (e.g., "SBIN.NS").
- When providing NSE data, mention the source (e.g., "Data from NSE") and timeliness (e.g., "as of the last trading day") if applicable.
- Combine NSE data with *python_repl* to perform advanced analysis, such as calculating moving averages, volatility, or risk metrics (e.g., Sharpe ratio) for better insights.

**Examples of NSE Tool Usage for Financial Analysis:**
- **Stock Analysis:** Use *Get_Price_Volume_Deliverable_Data* to fetch historical data for "SBIN" over 6 months (e.g., {"symbol": "SBIN", "period": "6M"}) and combine with *python_repl* to calculate a 50-day moving average or RSI for trend analysis.
- **Market Overview:** Use *Get_Market_Watch_All_Indices* (e.g., {}) for real-time NSE index data and *Get_Index_Data* (e.g., {"index": "NIFTY 50", "period": "1Y"}) to analyze yearly performance.
- **Company Fundamentals:** Use *Get_Financial_Results_For_Equity* (e.g., {"symbol": "RELIANCE", "fin_period": "Quarterly"}) to fetch financials and calculate P/E or ROE using *python_repl*.
- **Derivative Trading:** Use *Get_NSE_Live_Option_Chain* (e.g., {"symbol": "BANKNIFTY"}) to identify high open interest strikes and *Get_Future_Price_Volume_Data* (e.g., {"symbol": "BANKNIFTY", "instrument": "FUTIDX", "period": "1M"}) to track futures trends, calculating basis (spot-futures difference) with *python_repl*.
- **Market Sentiment:** Use *Get_Participant_Wise_Open_Interest* and *Get_Participant_Wise_Trading_Volume* (e.g., {"trade_date": "20-06-2023"}) to analyze FII/DII activity and infer market direction.
- **F&O Insights:** Use *Get_FNO_Bhav_Copy* (e.g., {"trade_date": "20-06-2023"}) for futures and options data and *Get_Expiry_Dates_Future* (e.g., {}) to inform users about upcoming expiries.


"Please execute the following steps and provide the final output. Do not just list the steps; actually perform the calculations and actions required."


**If user ask's about todays finance info**
*Step 1*
- Search the Search_The_Internet and google_search to gather latest informations about the topics.
*Step 2*
*Step 2*
- Parse the date and search for recent video's on the topic and get captions of the youtube video. Try to search for finance news youtube channels and gather data from there. 
*Step 3* 
- Get Yahoo Finance News about the topic.
*Step 4* 
- Get Latest Stock price if valid for the topic and identify if worth it.
*Step 5* 
- Get the NSB Data if valid for the topic.
*Step 6*
- After getting all this data do analysis and give user best results

**How to give recommendations**
*Step 1*
- Search the Search_The_Internet and google_search to gather latest informations about the topics.
*Step 2*
- Parse the date and search for recent video's on the topic and get captions of the youtube video.
*Step 3* 
- Get Yahoo Finance News about the topic.
*Step 4* 
- Get Latest Stock price if valid for the topic and identify if worth it.
*Step 5* 
- Get the NSB Data if valid for the topic.
*Step 6*
- After getting all this data do analysis and give user best recommendations 


**Retry Logic**
- Try to retry if you did not get it right in first try. 
- If some tool did not get you best results try another tool.
- Try to refine output and give best output to the user.
- There is no restrictions to the tools you can use them so instead of telling i can do it , perform the steps that you think and give the best results.

Please execute the following steps and provide the final output. Do not just list the steps; actually perform the calculations and actions required

## Schema for Tools in the Financial Assistant Prompt

The following schema details the tools available to the AI financial assistant, including their purpose, input parameters, and data types. This structure ensures clarity on how each tool should be called to assist Indian investors effectively.

---

### 1. Yahoo Finance
- **Purpose**: Fetch recent news articles for specific stock tickers.
- **Input**: 
  - `query`: string (e.g., "RELIANCE.NS")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"query": "RELIANCE.NS"}`)

---

### 2. Chroma_DB_Search
- **Purpose**: Retrieve information from financial news video transcripts.
- **Input**: 
  - `query`: string (e.g., "Indian stock market trends")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"query": "Indian stock market trends"}`)

---

### 3. Get_Stock_Prices
- **Purpose**: Fetch current stock prices.
- **Input**: 
  - `ticker`: string (e.g., "SBIN.NS")
- **Number of Inputs**: 1
- **Input Format**: Single string (e.g., `"SBIN.NS"`)

---

### 4. Web_Financial_Research
- **Purpose**: Conduct comprehensive stock research across multiple sources.
- **Input**: 
  - `query`: string (e.g., "TCS stock analysis")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"query": "TCS stock analysis"}`)

---

### 5. Search_The_Internet
- **Purpose**: Perform general web searches for financial data, news, or advice.
- **Input**: 
  - `query`: string (e.g., "latest RBI monetary policy")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"query": "latest RBI monetary policy"}`)

---

### 6. Search_Youtube
- **Purpose**: Search YouTube for financial learning videos.
- **Input**: 
  - `query`: string (e.g., "how to invest in mutual funds India")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"query": "how to invest in mutual funds India"}`)

---

### 7. python_repl
- **Purpose**: Execute Python code for calculations and data analysis.
- **Input**: 
  - `code`: string (e.g., "import pandas as pd; data = [100, 110, 105]; pd.Series(data).mean()")
- **Number of Inputs**: 1
- **Input Format**: Single string (e.g., `"import pandas as pd; data = [100, 110, 105]; pd.Series(data).mean()"`)

---

### 8. Get_Price_Volume_Deliverable_Data
- **Purpose**: Fetch historical price, volume, and deliverable data for a stock.
- **Inputs**: 
  - `symbol`: string (e.g., "SBIN") – Required
  - `from_date`: string (e.g., "01-01-2023") – Optional
  - `to_date`: string (e.g., "31-12-2023") – Optional
  - `period`: string (e.g., "1M") – Optional
- **Number of Inputs**: 1 to 4
- **Input Format**: Dictionary (e.g., `{"symbol": "SBIN", "period": "1M"}`)

---

### 9. Get_Index_Data
- **Purpose**: Retrieve historical data on NSE indices.
- **Inputs**: 
  - `index`: string (e.g., "NIFTY 50") – Required
  - `from_date`: string – Optional
  - `to_date`: string – Optional
  - `period`: string (e.g., "6M") – Optional
- **Number of Inputs**: 1 to 4
- **Input Format**: Dictionary (e.g., `{"index": "NIFTY 50", "period": "6M"}`)

---

### 10. Get_Bhav_Copy_With_Delivery
- **Purpose**: Get daily market data with delivery details for a trade date.
- **Input**: 
  - `trade_date`: string (e.g., "15-08-2023")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"trade_date": "15-08-2023"}`)

---

### 11. Get_Equity_List
- **Purpose**: Provide a list of all NSE equities.
- **Inputs**: None
- **Number of Inputs**: 0
- **Input Format**: Empty dictionary (e.g., `{}`)

---

### 12. Get_FNO_Equity_List
- **Purpose**: Fetch derivative equities with lot sizes.
- **Inputs**: None
- **Number of Inputs**: 0
- **Input Format**: Empty dictionary (e.g., `{}`)

---

### 13. Get_Market_Watch_All_Indices
- **Purpose**: Obtain current market data for all NSE indices.
- **Inputs**: None
- **Number of Inputs**: 0
- **Input Format**: Empty dictionary (e.g., `{}`)

---

### 14. Get_Financial_Results_For_Equity
- **Purpose**: Retrieve financial results for equities.
- **Inputs**: 
  - `symbol`: string (e.g., "RELIANCE") – Required
  - `from_date`: string – Optional
  - `to_date`: string – Optional
  - `period`: string – Optional
  - `fo_sec`: boolean – Optional
  - `fin_period`: string (e.g., "Quarterly") – Optional
- **Number of Inputs**: 1 to 6
- **Input Format**: Dictionary (e.g., `{"symbol": "RELIANCE", "fin_period": "Quarterly"}`)

---

### 15. Get_Future_Price_Volume_Data
- **Purpose**: Access historical futures price and volume data.
- **Inputs**: 
  - `symbol`: string (e.g., "BANKNIFTY") – Required
  - `instrument`: string (e.g., "FUTIDX") – Required
  - `from_date`: string – Optional
  - `to_date`: string – Optional
  - `period`: string (e.g., "1M") – Optional
- **Number of Inputs**: 2 to 5
- **Input Format**: Dictionary (e.g., `{"symbol": "BANKNIFTY", "instrument": "FUTIDX", "period": "1M"}`)

---

### 16. Get_Option_Price_Volume_Data
- **Purpose**: Fetch historical options price and volume data.
- **Inputs**: 
  - `symbol`: string (e.g., "NIFTY") – Required
  - `instrument`: string (e.g., "OPTIDX") – Required
  - `option_type`: string (e.g., "CE") – Required
  - `from_date`: string – Optional
  - `to_date`: string – Optional
  - `period`: string (e.g., "1M") – Optional
- **Number of Inputs**: 3 to 6
- **Input Format**: Dictionary (e.g., `{"symbol": "NIFTY", "instrument": "OPTIDX", "option_type": "CE", "period": "1M"}`)

---

### 17. Get_FNO_Bhav_Copy
- **Purpose**: Retrieve F&O bhav copy for a specific trade date.
- **Input**: 
  - `trade_date`: string (e.g., "20-06-2023")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"trade_date": "20-06-2023"}`)

---

### 18. Get_Participant_Wise_Open_Interest
- **Purpose**: Get open interest data by participant type.
- **Input**: 
  - `trade_date`: string (e.g., "20-06-2023")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"trade_date": "20-06-2023"}`)

---

### 19. Get_Participant_Wise_Trading_Volume
- **Purpose**: Fetch trading volume data by participant type.
- **Input**: 
  - `trade_date`: string (e.g., "20-06-2023")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"trade_date": "20-06-2023"}`)

---

### 20. Get_FII_Derivatives_Statistics
- **Purpose**: Access FII derivatives trading statistics.
- **Input**: 
  - `trade_date`: string (e.g., "20-06-2023")
- **Number of Inputs**: 1
- **Input Format**: Dictionary (e.g., `{"trade_date": "20-06-2023"}`)

---

### 21. Get_Expiry_Dates_Future
- **Purpose**: Retrieve future expiry dates.
- **Inputs**: None
- **Number of Inputs**: 0
- **Input Format**: Empty dictionary (e.g., `{}`)

---

### 22. Get_NSE_Live_Option_Chain
- **Purpose**: Fetch live option chain data.
- **Inputs**: 
  - `symbol`: string (e.g., "BANKNIFTY") – Required
  - `expiry_date`: string – Optional
  - `oi_mode`: string (e.g., "full") – Optional
- **Number of Inputs**: 1 to 3
- **Input Format**: Dictionary (e.g., `{"symbol": "BANKNIFTY", "oi_mode": "full"}`)

---

### 23 Get_Youtube_Captions
- **Purpose**: Fetch Captions/Subtitle of Youtube Video
- **Inputs**:
    - `video_id`: string - Required
- **Input Format**: List (e.g., `['abc','def']` )

## Notes on the Schema
- **Input Formats**: Most tools expect a dictionary with key-value pairs, except for `Get_Stock_Prices` and `python_repl`, which take a single string.
- **Optional Parameters**: Tools with optional inputs (e.g., `from_date`, `to_date`) allow flexibility in data retrieval.
- **Usage Context**: This schema enhances the `self.state` prompt by providing a structured guide for invoking each tool, ensuring the AI assistant can deliver precise financial insights to users.

**CRITICAL DISCLAIMER:** This guidance is general financial advice. All investment decisions should involve personal research and potential professional consultation. Investments carry inherent risks, and past performance does not guarantee future results.”"""
                )
            ]
        }

        self.graph = self._build_graph()

    def comprehensive_stock_research(self, ticker: str, max_sources: int = 3):
        """
        Perform comprehensive web-based research on a stock.

        Args:
            ticker (str): Stock ticker symbol
            max_sources (int): Maximum number of sources to retrieve from each search type

        Returns:
            str: Comprehensive financial research report
        """
        # Ensure ticker is in the correct format for Indian stocks
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker = f"{ticker}.NS"  # Default to NSE

        # Initialize research components
        research_sections = []

        # 1. Stock Price and Basic Information
        try:
            stock_price_info = self.chat_tools.get_stock_prices(ticker)
            research_sections.append(
                "🏦 Stock Price and Basic Information:\n" + stock_price_info
            )
        except Exception as e:
            research_sections.append(f"❌ Stock Price Info Error: {str(e)}")

        # 2. Web Search for Company Overview
        try:
            company_search = self.chat_tools.search_web(
                f"{ticker} company overview", max_results=max_sources
            )
            research_sections.append("\n🌐 Company Overview:\n" + company_search)
        except Exception as e:
            research_sections.append(f"❌ Company Overview Search Error: {str(e)}")

        # 3. Recent News
        try:
            news_search = self.chat_tools.search_web(
                f"{ticker} recent news financial", max_results=max_sources
            )
            research_sections.append(
                "\n📰 Recent News and Market Sentiment:\n" + news_search
            )
        except Exception as e:
            research_sections.append(f"❌ News Search Error: {str(e)}")

        # 4. Financial Performance
        try:
            financial_search = self.chat_tools.search_web(
                f"{ticker} financial performance quarterly results",
                max_results=max_sources,
            )
            research_sections.append("\n💹 Financial Performance:\n" + financial_search)
        except Exception as e:
            research_sections.append(f"❌ Financial Performance Search Error: {str(e)}")

        # 5. Analyst Recommendations
        try:
            analyst_search = self.chat_tools.search_web(
                f"{ticker} analyst recommendations target price",
                max_results=max_sources,
            )
            research_sections.append("\n🔍 Analyst Recommendations:\n" + analyst_search)
        except Exception as e:
            research_sections.append(
                f"❌ Analyst Recommendations Search Error: {str(e)}"
            )

        # Combine and format the research
        full_research = "\n\n".join(research_sections)

        # Add a comprehensive disclaimer
        disclaimer = (
            "\n\n⚠️ DISCLAIMER:\n"
            "This research is compiled from web sources and AI analysis. "
            "It is NOT financial advice. Always consult professional financial advisors, "
            "conduct your own due diligence, and be aware that market conditions can change rapidly."
        )

        return full_research + disclaimer

    def stock_analysis_pipeline(chat_service):
        """
        A comprehensive pipeline for stock analysis that:
        1. Retrieves full equity list
        2. Filters stocks based on liquidity and volatility
        3. Performs in-depth research on top candidates
        4. Generates a detailed investment report
        """
        # Step 1: Get Full Equity List
        print("🔍 Step 1: Retrieving Full Equity List")
        equity_list = chat_service.chat_tools.get_equity_list()
        print(f"Total Equities Found: {len(equity_list)}")

        # Step 2: Analyze Price and Volume for Potential Candidates
        print("\n🧮 Step 2: Analyzing Stock Liquidity and Volatility")
        top_candidates = []

        # Analyze top 20 stocks from the list
        for stock in equity_list[:20]:
            try:
                # Get 1-month price and volume data
                stock_data = (
                    chat_service.chat_tools.get_price_volume_and_deliverable_data(
                        {"symbol": stock, "period": "1M"}
                    )
                )

                # Basic analysis criteria
                if stock_data:
                    # Extract key metrics from the data
                    avg_volume = float(
                        stock_data.split("Average Volume:")[1].split("\n")[0].strip()
                    )
                    avg_price = float(
                        stock_data.split("Average Price:")[1].split("\n")[0].strip()
                    )
                    volatility = float(
                        stock_data.split("Volatility:")[1]
                        .split("\n")[0]
                        .strip()
                        .replace("%", "")
                    )

                    # Filter criteria: Good volume, moderate volatility
                    if avg_volume > 100000 and 10 <= volatility <= 30:
                        top_candidates.append(
                            {
                                "symbol": stock,
                                "avg_volume": avg_volume,
                                "avg_price": avg_price,
                                "volatility": volatility,
                            }
                        )
            except Exception as e:
                print(f"Error processing {stock}: {e}")

        print(f"Top Candidates Found: {len(top_candidates)}")

        # Step 3: Comprehensive Research on Top Candidates
        print("\n🔬 Step 3: Comprehensive Stock Research")
        detailed_research = []

        for candidate in top_candidates[:5]:  # Limit to top 5 candidates
            stock = candidate["symbol"]
            print(f"\nResearching {stock}")

            # Comprehensive web financial research
            web_research = chat_service.comprehensive_stock_research(stock)

            # Get recent financial results
            try:
                financial_results = (
                    chat_service.chat_tools.get_financial_results_for_equity(
                        {"symbol": stock, "fin_period": "Quarterly"}
                    )
                )
            except Exception as e:
                financial_results = f"Could not fetch financial results: {e}"

            # Get recent news
            try:
                recent_news = chat_service.yahoo_finance_tool.invoke(
                    {"query": f"{stock}.NS"}
                )
            except Exception as e:
                recent_news = f"Could not fetch news: {e}"

            detailed_research.append(
                {
                    "symbol": stock,
                    "candidate_metrics": candidate,
                    "web_research": web_research,
                    "financial_results": financial_results,
                    "recent_news": recent_news,
                }
            )

        # Step 4: Generate Investment Report
        print("\n📊 Step 5: Generating Investment Report")
        investment_report = "# Comprehensive Stock Investment Analysis Report\n\n"

        for research in detailed_research:
            investment_report += f"""
    ## Stock: {research["symbol"]}

    ### Performance Metrics
    - Average Volume: {research["candidate_metrics"]["avg_volume"]:,.0f}
    - Average Price: ₹{research["candidate_metrics"]["avg_price"]:.2f}
    - Volatility: {research["candidate_metrics"]["volatility"]}%

    ### Web Research Insights
    {research["web_research"]}

    ### Financial Results
    {research["financial_results"]}

    ### Recent News
    {research["recent_news"]}

    ---
    """

        return investment_report

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
        llm_with_tools = self.llm.bind_tools(self.tools)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(self, state: State):
        """Execute tool calls and return results."""
        last_message = state["messages"][-1]
        tool_results = []
        for tool_call in last_message.tool_calls:
            tool = next(t for t in self.tools if t.name == tool_call["name"])
            result = tool.invoke(tool_call["args"])
            tool_results.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
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
            # If the content is a list, join its elements into a single string
            last_content = "\n".join(str(item) for item in last_content)
        return last_content

    async def stream_input(self, user_input: str) -> AsyncGenerator[str, None]:
        # Append user input to existing messages to preserve conversation history
        self.state["messages"].append(HumanMessage(content=user_input))
        # Record the initial number of messages to identify new ones
        initial_length = len(self.state["messages"])

        # Stream state updates from the graph
        async for state_update in self.graph.astream(self.state, stream_mode="values"):
            self.state = state_update
            # Get messages added after the user input
            new_messages = self.state["messages"][initial_length:]
            # Process each new message
            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    content = msg.content
                    # Join list content into a string if necessary
                    if isinstance(content, list):
                        content = "\n".join(str(item) for item in content)
                    yield content
            # Update initial_length to avoid re-yielding old messages
            initial_length = len(self.state["messages"])
