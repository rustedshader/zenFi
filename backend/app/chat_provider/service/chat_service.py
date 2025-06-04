import os
from typing import AsyncGenerator
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import select
from app.chat_provider.service.chat_service_prompt import SYSTEM_INSTRUCTIONS
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.runnables import RunnableConfig
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
    get_stock_point_change,
    get_stock_percentage_change,
    get_stock_price_change,
)
from app.chat_provider.tools.web_search_tools import (
    google_search_tool,
    duckduckgo_search_run_tool,
    duckduckgo_search_results_tool,
    brave_search_tool,
)
from app.chat_provider.tools.news_tools import (
    fetch_finance_news,
    duckduckgo_news_search_tool,
)
from app.chat_provider.tools.basic_tools import (
    get_current_datetime,
    youtube_search_tool,
)

from app.chat_provider.models.chat_models import AppState
from app.chat_provider.tools.rag_tools import (
    get_db,
    get_user_portfolio_tool,
    ingested_web_search,
)
from app.api.api_models import ChatSession


class ChatService:
    def __init__(
        self,
        model: ChatGoogleGenerativeAI,
    ):
        self.model = model
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
            get_stock_point_change,
            get_stock_percentage_change,
            get_stock_price_change,
            google_search_tool,
            brave_search_tool,
            duckduckgo_search_results_tool,
            duckduckgo_search_run_tool,
            fetch_finance_news,
            duckduckgo_news_search_tool,
            get_current_datetime,
            youtube_search_tool,
            get_user_portfolio_tool,
            ingested_web_search,
        ]
        self.tool_node = ToolNode(self.tools)
        self.system_prompt_message = SystemMessage(
            content=SYSTEM_INSTRUCTIONS
            + "\n\nYou will be provided with search results related to the user's query. Use this information to provide accurate and up-to-date responses. Additionally, if you think a YouTube video would be helpful for the user's query, use the YouTubeSearchTool to find a relevant video and include the link in your response."
            + "\n\nAdditionally, you have access to ingested web documents on specific topics. Use the 'ingested_web_search' tool with the appropriate context when the user's query relates to these topics. Available contexts include: 'langsmith_pricing', 'cloud_workstations', 'bigframes', 'dataplex'."
        )
        self.bound_llm = self.model.bind_tools(self.tools)

    # TODO: Can Use Pydantic model here to get structured output for the llm
    async def determine_search_need(self, state: AppState):
        """
        Use LLM to determine if web search is needed for the user's query.
        """
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content

            # Create a prompt to determine if search is needed
            search_decision_prompt = f"""
            Analyze the following user query and determine if a web search is needed to answer it properly.

            User Query: "{user_input}"

            Available tools include:
            - Stock data tools (prices, market cap, volume, historical data, etc.)
            - Portfolio tools (user's personal portfolio information)
            - Finance news tools
            - Current datetime
            - YouTube search
            - Ingested web documents on specific topics

            Consider these guidelines:
            1. If the query can be answered using stock data tools (e.g., stock prices, financial metrics), NO web search is needed
            2. If the query is about user's portfolio, NO web search is needed
            3. If the query asks for current news, market trends, or recent events, web search IS needed
            4. If the query asks for general information not covered by available tools, web search IS needed
            5. If the query asks for explanations, tutorials, or educational content, web search MAY be needed

            Respond with ONLY "YES" if web search is needed, or "NO" if it's not needed.
            """

            response = await self.model.ainvoke(
                [
                    SystemMessage(
                        content="You are an expert at determining information requirements."
                    ),
                    HumanMessage(content=search_decision_prompt),
                ]
            )

            needs_search = response.content.strip().upper() == "YES"
            print(
                f"DEBUG [determine_search_need]: Query: '{user_input}', Needs search: {needs_search}"
            )

            return {"needs_web_search": needs_search}

        return {"needs_web_search": False}

    async def generate_multiple_queries(self, state: AppState):
        number_of_search_queries = 3
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content
            query_prompt = f"Based on the following user input, generate {number_of_search_queries} distinct search queries to find comprehensive information: {user_input}"
            query_response = await self.model.ainvoke(
                [
                    SystemMessage(content="You are a helpful financial assistant."),
                    HumanMessage(content=query_prompt),
                ]
            )
            queries = query_response.content.split("\n")
            return {"search_queries": queries}
        return {}

    async def perform_multiple_searches(self, state: AppState):
        queries = state.get("search_queries", [])
        search_results = []
        for query in queries:
            search_tool = google_search_tool
            try:
                result = await search_tool.ainvoke({"query": query})
                search_results.append(result)
            except Exception as e:
                search_results.append(f"Search failed for '{query}': {str(e)}")
        combined_results = "\n\n".join(search_results)
        search_message = SystemMessage(
            content=f"Search results for queries '{', '.join(queries)}': {combined_results}"
        )
        return {"messages": [search_message]}

    async def evaluate_search_results(self, state: MessagesState):
        messages = state["messages"]
        last_message = messages[-1]
        if (
            isinstance(last_message, SystemMessage)
            and "Search results" in last_message.content
        ):
            if last_message.content.strip():
                return {"search_sufficient": True}
            else:
                return {"search_sufficient": False}
        return {"search_sufficient": False}

    async def check_portfolio_query(self, state: AppState):
        last_message = state["messages"][-1]
        needs_portfolio_flag = False
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content.lower()
            portfolio_keywords = [
                "portfolio",
                "assets",
                "holdings",
                "my stocks",
                "what stocks are in it",
            ]
            if any(keyword in user_input for keyword in portfolio_keywords):
                needs_portfolio_flag = True
        print(
            f"DEBUG [check_portfolio_query]: User input: '{user_input}', Detected needs_portfolio: {needs_portfolio_flag}"
        )
        return {"needs_portfolio": needs_portfolio_flag}

    async def call_model(self, state: AppState, config: RunnableConfig):
        if config:
            current_user_id = config["configurable"].get("user_id")

        llm_messages = [self.system_prompt_message]
        llm_messages.extend(state["messages"])

        if state.get("needs_portfolio"):
            if current_user_id:
                portfolio_system_message = SystemMessage(
                    content=f"The user is asking about their portfolio. Their user ID is '{current_user_id}'. "
                    f"You MUST use the 'get_user_portfolio_tool' to fetch their default portfolio data. "
                    f"When calling 'get_user_portfolio_tool', ensure you provide the 'user_id' argument with the exact value '{current_user_id}'."
                )
            else:
                portfolio_system_message = SystemMessage(
                    content="The user is asking about their portfolio. You need a user ID to call 'get_user_portfolio_tool'. "
                    "If you don't have it and it hasn't been provided by the system, you may need to ask the user for their user ID."
                )
            llm_messages.append(portfolio_system_message)

        response = await self.bound_llm.ainvoke(llm_messages)
        print("Model response:", response)
        return {"messages": [response]}

    def should_continue(self, state: AppState):
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            if last_message.tool_calls:
                return "tools"
        return "generate_summary"

    def route_after_search_decision(self, state: AppState):
        """
        Route based on whether web search is needed and portfolio check.
        """
        needs_search = state.get("needs_web_search", False)
        needs_portfolio = state.get("needs_portfolio", False)

        if needs_portfolio:
            return "call_model"
        elif needs_search:
            return "generate_multiple_queries"
        else:
            return "call_model"

    async def generate_summary(self, state: AppState, config: RunnableConfig):
        try:
            messages = state["messages"]
            if not messages:
                return {"summary": "No conversation to summarize."}

            recent_messages = messages[-3:] if len(messages) >= 3 else messages
            conversation = "\n".join(
                f"{msg.type}: {msg.content}" for msg in recent_messages
            )
            heading_prompt = f"Provide a concise heading (max 5 words) that best describes the following conversation. This will be used as a chat title.\n\n{conversation}"
            response = await self.model.ainvoke(
                [
                    SystemMessage(content="You are a helpful assistant."),
                    HumanMessage(content=heading_prompt),
                ]
            )
            heading = response.content.strip()
            if config:
                session_id = config["configurable"].get("session_id")
                print("Got Session id ", session_id)
            else:
                print("No config Found")

            if not heading:
                heading = "Heading generation failed."
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            async for db in get_db():
                res = await db.execute(stmt)
                chat_session = res.scalar_one_or_none()
                if chat_session:
                    chat_session.summary = heading
                    await db.commit()
            return {"summary": heading}
        except Exception as e:
            return {"summary": f"Error generating heading: {str(e)}"}

    def build_graph(self, checkpointer):
        builder = StateGraph(AppState)

        # Add all nodes
        builder.add_node("check_portfolio_query", self.check_portfolio_query)
        builder.add_node("determine_search_need", self.determine_search_need)
        builder.add_node("generate_multiple_queries", self.generate_multiple_queries)
        builder.add_node("perform_multiple_searches", self.perform_multiple_searches)
        builder.add_node("evaluate_search_results", self.evaluate_search_results)
        builder.add_node("call_model", self.call_model)
        builder.add_node("tools", self.tool_node)
        builder.add_node("generate_summary", self.generate_summary)

        # Build the flow
        builder.add_edge(START, "check_portfolio_query")
        builder.add_edge("check_portfolio_query", "determine_search_need")

        # Route after determining search need
        builder.add_conditional_edges(
            "determine_search_need",
            self.route_after_search_decision,
            {
                "call_model": "call_model",
                "generate_multiple_queries": "generate_multiple_queries",
            },
        )

        # Search flow (only executed if search is needed)
        builder.add_edge("generate_multiple_queries", "perform_multiple_searches")
        builder.add_edge("perform_multiple_searches", "evaluate_search_results")
        builder.add_conditional_edges(
            "evaluate_search_results",
            lambda state: "generate_multiple_queries"
            if not state.get("search_sufficient", False)
            else "call_model",
        )

        # Model flow
        builder.add_conditional_edges(
            "call_model", self.should_continue, ["tools", "generate_summary"]
        )
        builder.add_edge("tools", "call_model")
        builder.add_edge("generate_summary", END)

        self.graph = builder.compile(checkpointer=checkpointer)
        return self.graph

    async def stream_input(
        self, user_input: str, thread_id: str, user_id: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        config = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
                "session_id": session_id,
            }
        )
        input_state = {"messages": [HumanMessage(content=user_input)]}
        async for state_update_values in self.graph.astream(
            input_state, config, stream_mode="values"
        ):
            last_message = state_update_values["messages"][-1]
            if "search_queries" in state_update_values:
                print("Search Query", state_update_values["search_queries"])
            if isinstance(last_message, AIMessage):
                content = last_message.content
                if isinstance(content, list):
                    content_str = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            content_str += item["text"] + "\n"
                        else:
                            content_str += str(item) + "\n"
                    content = content_str.strip()
                if content:
                    yield content


if __name__ == "__main__":
    import asyncio

    GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
    )

    async def main():
        DB_URI = "postgresql://postgres:postgres@localhost:5434/postgres"
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            chat_service = ChatService(model=model)
            chat_service.build_graph(checkpointer)
            thread_id = "0103"
            print("\nStreaming responses:")
            async for chunk in chat_service.stream_input(
                "What is the current price of AAPL?", thread_id, "1", "session_1"
            ):
                print(chunk)

    asyncio.run(main())
