import os
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from app.chat_provider.tools.finance_tools import (
    get_stock_currency,
    get_stock_day_high,
    get_stock_day_low,
    get_stock_exchange,
    get_stock_fifty_day_average,
    get_stock_history,
    get_stock_income_statement,
    get_stock_info,
    get_stock_last_price,
    get_stock_last_volume,
    get_stock_market_cap,
    get_stock_open,
    get_stock_options_chain,
    get_stock_previous_close,
    get_stock_quote_type,
    get_stock_regular_market_previous_close,
    get_stock_shares,
    get_stock_ten_day_average_volume,
    get_stock_three_month_average_volume,
    get_stock_timezone,
    get_stock_two_hundred_day_average,
    get_stock_year_change,
    get_stock_year_high,
    get_stock_year_low,
)
from app.chat_provider.tools.web_search_tools import (
    google_search_tool,
    duckduckgo_search_run_tool,
    duckduckgo_search_results_tool,
    brave_search_tool,
)

SYSTEM_PROMPT = """
You are a portfolio analyser and portfolio summary generator based on user portfolio.
"""


class PortfolioSummaryService:
    def __init__(
        self,
        model: ChatGoogleGenerativeAI,
    ):
        # Initialize the model (Gemini)
        self.model = model
        # Define the tools
        self.tools = [
            get_stock_currency,
            get_stock_day_high,
            get_stock_day_low,
            get_stock_exchange,
            get_stock_fifty_day_average,
            get_stock_last_price,
            get_stock_last_volume,
            get_stock_market_cap,
            get_stock_open,
            get_stock_previous_close,
            get_stock_quote_type,
            get_stock_regular_market_previous_close,
            get_stock_shares,
            get_stock_ten_day_average_volume,
            get_stock_three_month_average_volume,
            get_stock_timezone,
            get_stock_two_hundred_day_average,
            get_stock_year_change,
            get_stock_year_high,
            get_stock_year_low,
            get_stock_history,
            get_stock_income_statement,
            get_stock_info,
            get_stock_options_chain,
            google_search_tool,
            brave_search_tool,
            duckduckgo_search_results_tool,
            duckduckgo_search_run_tool,
        ]
        # Tool Node
        self.tool_node = ToolNode(self.tools)
        # Set the system prompt
        self.system_prompt_message = SystemMessage(content=SYSTEM_PROMPT)
        # Bind tools to the model
        self.bound_llm = self.model.bind_tools(self.tools)
        self.graph = self.build_graph()

    async def call_model(self, state: MessagesState):
        messages = [self.system_prompt_message] + state["messages"]
        response = await self.bound_llm.ainvoke(messages)
        return {"messages": response}

    def should_continue(self, state: MessagesState):
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            if last_message.tool_calls:
                return "tools"
        else:
            print("Error: Last Message Instance is not AIMessage")
        return END

    def build_graph(self):
        # https://langchain-ai.github.io/langgraph/how-tos/tool-calling/#use-prebuilt-toolnode
        builder = StateGraph(MessagesState)
        builder.add_node("call_model", self.call_model)
        builder.add_node("tools", self.tool_node)
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model", self.should_continue, ["tools", END]
        )
        builder.add_edge("tools", "call_model")
        self.graph = builder.compile()
        return self.graph

    async def get_response(self, user_input: str) -> str:
        input_state = {"messages": [HumanMessage(content=user_input)]}
        async for state_update in self.graph.astream(input_state, stream_mode="values"):
            last_message = state_update["messages"][-1]
            if isinstance(last_message, AIMessage):
                content = last_message.content
                if isinstance(content, list):
                    content = "\n".join(str(item) for item in content)
                return content
        return ""


if __name__ == "__main__":
    GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
    )
