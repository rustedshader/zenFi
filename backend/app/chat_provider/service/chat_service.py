import os
from typing import AsyncGenerator
from langchain_sandbox import PyodideSandbox
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import select
from app.chat_provider.service.chat_service_prompt import (
    SYSTEM_INSTRUCTIONS,
    python_code_needed_decision_prompt,
    python_code_context_prompt,
    python_code_generation_prompt,
    generate_search_queries_system_prompt,
)
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
    duckduckgo_search_run_tool,
    duckduckgo_search_results_tool,
    brave_search_tool,
)
from app.chat_provider.tools.news_tools import (
    duckduckgo_news_search_tool,
)
from app.chat_provider.tools.basic_tools import (
    get_current_datetime,
    youtube_search_tool,
)

from app.chat_provider.models.chat_models import (
    AppState,
    PythonCode,
    PythonCodeContext,
    PythonSearchNeed,
    Queries,
)
from app.chat_provider.tools.rag_tools import (
    get_db,
)
from app.api.api_models import ChatSession, KnowledgeBase, Portfolio
from app.chat_provider.service.knowledge_base.knowledege_base import search_enhanced
from sqlalchemy.orm import selectinload

from app.chat_provider.utils.search_utils import (
    get_search_params,
    select_and_execute_search,
)

import datetime


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
            brave_search_tool,
            duckduckgo_search_results_tool,
            duckduckgo_search_run_tool,
            duckduckgo_news_search_tool,
            get_current_datetime,
            youtube_search_tool,
        ]
        self.tool_node = ToolNode(self.tools)
        self.system_prompt_message = SystemMessage(
            content=SYSTEM_INSTRUCTIONS
            + "\n\nYou will be provided with search results related to the user's query. Use this information to provide accurate and up-to-date responses. Additionally, if you think a YouTube video would be helpful for the user's query, use the YouTubeSearchTool to find a relevant video and include the link in your response."
        )
        self.bound_llm = self.model.bind_tools(self.tools)

    async def check_knowledge_base_query(self, state: AppState):
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content

            knowledge_base_decision_prompt = f"""
                        Analyze the user query to determine if it requires accessing their personal knowledge base, which contains their transaction history, portfolio, and financial notes.

                        User Query: "{user_input}"

                        Guidelines:
                        1. If the query uses personal pronouns like "my" or "I" in a financial context (e.g., "my portfolio," "my transactions," "what did I spend on"), the knowledge base IS needed.
                        2. If the query asks for analysis or uses superlatives about the user's finances (e.g., "what is my largest transaction," "my most recent stock purchase," "my top spending category"), the knowledge base IS needed.
                        3. If the query is about general financial topics, stock market data (e.g., "price of AAPL"), or news, the knowledge base is NOT needed.

                        Examples of queries that NEED the knowledge base:
                        - "hi can you query my knowledge base about my most spent transaction"
                        - "what is my largest transaction"
                        - "show me my recent purchases"
                        - "How much did I invest in tech stocks?"

                        Examples of queries that DO NOT NEED the knowledge base:
                        - "What is the market cap of Microsoft?"
                        - "Tell me the latest finance news."
                        - "Explain what a P/E ratio is."

                        Respond with ONLY "YES" if the knowledge base is needed, or "NO" if it's not.
                        """

            response = await self.model.ainvoke(
                [
                    SystemMessage(
                        content="You are an expert at determining information requirements."
                    ),
                    HumanMessage(content=knowledge_base_decision_prompt),
                ]
            )

            needs_knowledge_base = response.content.strip().upper() == "YES"
            print(
                f"DEBUG [check_knowledge_base_query]: Query: '{user_input}', Needs knowledge base: {needs_knowledge_base}"
            )

            return {"needs_knowledge_base": needs_knowledge_base}

        return {"needs_knowledge_base": False}

    async def search_knowledge_base(
        self, state: AppState, config: RunnableConfig
    ) -> dict:
        try:
            last_message = state["messages"][-1]
            if not isinstance(last_message, HumanMessage):
                print(
                    "DEBUG [search_knowledge_base]: Last message is not a HumanMessage"
                )
                return {"knowledge_base_results": "Invalid query format"}

            query = last_message.content
            print(
                f"DEBUG [search_knowledge_base]: Searching knowledge base for query: '{query}'"
            )

            # Get user_id from config
            user_id = (
                config["configurable"].get("user_id")
                if config and "configurable" in config
                else None
            )
            if not user_id:
                print("DEBUG [search_knowledge_base]: No user_id found in config")
                return {
                    "knowledge_base_results": "No user ID found. Cannot search knowledge base."
                }

            async for db in get_db():
                stmt = select(KnowledgeBase).where(
                    KnowledgeBase.is_default,
                    KnowledgeBase.user_id == int(user_id),
                )
                result = await db.execute(stmt)
                knowledge_base = result.scalar_one_or_none()

                if not knowledge_base:
                    print("DEBUG [search_knowledge_base]: No knowledge base found")
                    return {
                        "knowledge_base_results": "No knowledge base found. Please create or select a knowledge base."
                    }

                kb_table_id = str(knowledge_base.table_id)
                if not kb_table_id:
                    print(
                        "DEBUG [search_knowledge_base]: Knowledge base has no table_id"
                    )
                    return {
                        "knowledge_base_results": "Knowledge base has no table_id set."
                    }

                try:
                    rag_result = search_enhanced(
                        table_id=kb_table_id,
                        query=query,
                        filter={"context": "some_context"},
                    )
                    if rag_result.get("answer"):
                        print(
                            f"DEBUG [search_knowledge_base]: Found answer: {rag_result['answer']}"
                        )
                        return {"knowledge_base_results": rag_result["answer"]}
                    else:
                        print("DEBUG [search_knowledge_base]: No answer found")
                        return {
                            "knowledge_base_results": "No relevant information found in the knowledge base."
                        }
                except Exception as e:
                    print(f"ERROR [search_knowledge_base]: Search failed: {str(e)}")
                    return {
                        "knowledge_base_results": f"Error searching knowledge base: {str(e)}"
                    }

            return {"knowledge_base_results": "Database connection failed."}

        except Exception as e:
            print(f"ERROR [search_knowledge_base]: Unexpected error: {str(e)}")
            return {"knowledge_base_results": f"Unexpected error: {str(e)}"}

    async def determine_search_need(self, state: AppState):
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content

            search_decision_prompt = f"""
            Analyze the following user query and determine if a web search is needed to answer it properly.

            User Query: "{user_input}"

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
        number_of_search_queries = 5
        last_message = state["messages"][-1]
        todays_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if isinstance(last_message, HumanMessage):
            user_input = last_message.content
            formatted_search_queries_system_prompt = (
                generate_search_queries_system_prompt.format(
                    date=todays_date,
                    number_of_search_queries=number_of_search_queries,
                    query=user_input,
                )
            )
            structured_llm = self.model.with_structured_output(Queries)
            queries = await structured_llm.ainvoke(
                [
                    SystemMessage(content=formatted_search_queries_system_prompt),
                    HumanMessage(
                        content="Generate search queries based on the user's input."
                    ),
                ]
            )
            return {"search_queries": queries.queries}
        return {}

    async def search_web(self, state: AppState, config: RunnableConfig):
        """Execute web searches for the section queries."""
        search_queries = state["search_queries"]
        search_api = config["configurable"].get("search_api", "googlesearch")
        search_api_config = config["configurable"].get("search_api_config", {})
        params_to_pass = get_search_params(search_api, search_api_config)

        query_list = [
            query.search_query
            for query in search_queries
            if query.search_query is not None
        ]

        source_str = await select_and_execute_search(
            search_api, query_list, params_to_pass
        )

        return {
            "source_str": source_str,
        }

    async def evaluate_search_results(self, state: AppState):
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

    async def generate_portfolio_data(self, state: AppState, config: RunnableConfig):
        if config:
            current_user_id = config["configurable"].get("user_id")
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == int(current_user_id))
            .where(Portfolio.is_default)
            .options(selectinload(Portfolio.assets))
        )
        try:
            async for db in get_db():
                result = await db.execute(stmt)
                portfolios = result.scalars().all()
                if not portfolios:
                    return {"portfolio_data": ""}

                output_lines = []
                for portfolio in portfolios:
                    created_at = str(portfolio.created_at)
                    description = str(portfolio.description)

                    output_lines.append(f"Portfolio Name: {portfolio.name}")
                    output_lines.append(f"Created At: {created_at}")
                    output_lines.append(f"Description: {description}")
                    if portfolio.assets:
                        output_lines.append("Assets:")
                        for asset in portfolio.assets:
                            symbol = getattr(asset, "identifier", "N/A")
                            created_at = getattr(asset, "created_at", "N/A")
                            asset_id = getattr(asset, "id", "N/A")
                            asset_type = getattr(asset, "asset_type", "N/A")
                            quantity = getattr(asset, "quantity", "N/A")
                            purchase_price = getattr(asset, "purchase_price", "N/A")
                            purchase_date = getattr(asset, "purchase_date", "N/A")
                            current_value = getattr(asset, "current_value", "N/A")
                            notes = getattr(asset, "notes", "N/A")
                            output_lines.append(
                                f"  - Asset ID: {asset_id}, Asset Type: {asset_type}, Symbol: {symbol}, Created At: {created_at}, Quantity: {quantity}, Purchase Price: {purchase_price}, Purchase Date: {purchase_date}, Current Value: {current_value}, Notes: {notes}"
                            )
                    else:
                        output_lines.append("Assets: None")
                    output_lines.append("")
                    return {"portfolio_data": "\n".join(output_lines).strip()}
                print(
                    f"DEBUG [generate_portfolio_data]: Generated portfolio data for user {current_user_id}"
                )
                print("DEBUG [generate_portfolio_data]: Output lines:", output_lines)

                return {"portfolio_data": "\n".join(output_lines).strip()}
        except Exception as e:
            print(f"ERROR [search_portfolio]: {str(e)}")
            return f"Error fetching portfolio: {str(e)}"

    async def call_model(self, state: AppState):
        llm_messages = [self.system_prompt_message]
        llm_messages.extend(state["messages"])

        additional_context = []

        if state.get("needs_portfolio"):
            if state.get("portfolio_data"):
                additional_context.append(
                    f"User Portfolio Data:\n{state['portfolio_data']}"
                )

        if state.get("needs_knowledge_base"):
            if state.get("knowledge_base_results"):
                additional_context.append(
                    f"Knowledge Base Results:\n{state['knowledge_base_results']}"
                )
        if state.get("needs_web_search"):
            if state.get("source_str"):
                additional_context.append(f"Web Search Results:\n{state['source_str']}")

        if state.get("needs_python_code"):
            if state.get("execution_result"):
                additional_context.append(
                    f"Python Execution Result:\n{state['execution_result']}"
                )

        if additional_context:
            context_message = SystemMessage(
                content="Additional Context for Response:\n\n"
                + "\n\n".join(additional_context)
            )
            llm_messages.append(context_message)

        response = await self.bound_llm.ainvoke(llm_messages)
        return {"messages": [response]}

    def route_after_search_decision(self, state: AppState):
        """
        Route based on whether web search, portfolio, or knowledge base check is needed.
        """
        needs_search = state.get("needs_web_search", False)
        needs_portfolio = state.get("needs_portfolio", False)
        needs_knowledge_base = state.get("needs_knowledge_base", False)

        if needs_portfolio or needs_knowledge_base:
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

    async def check_python_code_needed(self, state: AppState) -> dict:
        try:
            if not state["messages"]:
                return False

            last_message = state["messages"][-1]

            if not isinstance(last_message, HumanMessage):
                return False

            structured_llm = self.model.with_structured_output(PythonSearchNeed)

            formatted_prompt = python_code_needed_decision_prompt.format(
                user_query=last_message
            )

            response = await structured_llm.ainvoke(
                [
                    SystemMessage(content=formatted_prompt),
                    HumanMessage(content="Does Python Code Generation needed ? "),
                ]
            )

            print("LOG:", response.needs_python_code)

            if hasattr(response, "needs_python_code"):
                needs_python_code = response.needs_python_code
            elif (
                hasattr(response, "content")
                and isinstance(response.content, dict)
                and "needs_python_code" in response.content
            ):
                needs_python_code = response.content["needs_python_code"]
            else:
                print(
                    f"DEBUG [check_python_code_needed]: Empty or invalid response for query: '{last_message}'"
                )
                return {"needs_python_code": False}

            print(
                f"DEBUG [check_python_code_needed]: Query: '{last_message}', Needs Python code: {needs_python_code}"
            )

            return {"needs_python_code": needs_python_code}

        except Exception as e:
            print(
                f"ERROR [check_python_code_needed]: Failed to process query: {str(e)}"
            )
            return {"needs_python_code": False}

    async def generate_python_code_context(self, state: AppState):
        try:
            if not state["messages"]:
                return {"python_code_context": None}

            last_message = state["messages"][-1]
            if not isinstance(last_message, HumanMessage):
                return {"python_code_context": None}

            if not state.get("needs_python_code", False):
                print(
                    f"DEBUG [generate_python_code_context]: Python code generation not needed for query: '{last_message.content}'"
                )
                return {"python_code_context": None}

            structured_llm = self.model.with_structured_output(PythonCodeContext)
            formatted_prompt = python_code_context_prompt.format(
                user_query=last_message.content
            )

            response = await structured_llm.ainvoke(
                [
                    SystemMessage(content=formatted_prompt),
                    HumanMessage(
                        content="Provide the Python code context for the user's query."
                    ),
                ]
            )

            python_code_context = getattr(response, "python_code_context", None)
            if not python_code_context:
                print(
                    f"DEBUG [generate_python_code_context]: No context generated for query: '{last_message.content}'"
                )
                return {"python_code_context": None}

            print(
                f"DEBUG [generate_python_code_context]: Query: '{last_message.content}', Context: {python_code_context}"
            )
            return {"python_code_context": python_code_context}

        except Exception as e:
            print(
                f"ERROR [generate_python_code_context]: Failed to process query: {str(e)}"
            )
            return {"python_code_context": None}

    async def generate_python_code(self, state: AppState):
        try:
            if not state["messages"] or not state.get("needs_python_code", False):
                return {"python_code": None}

            last_message = state["messages"][-1]
            if not isinstance(last_message, HumanMessage):
                return {"python_code": None}

            python_code_context = state.get("python_code_context")
            if not python_code_context:
                print(
                    f"DEBUG [generate_python_code]: No context available for query: '{last_message.content}'"
                )
                return {"python_code": None}

            structured_llm = self.model.with_structured_output(PythonCode)
            formatted_prompt = python_code_generation_prompt.format(
                user_query=last_message.content, prompt=python_code_context
            )

            response = await structured_llm.ainvoke(
                [
                    SystemMessage(content=formatted_prompt),
                    HumanMessage(content="Generate Python code."),
                ]
            )
            python_code = getattr(response, "code", None)

            if not python_code:
                print(
                    f"DEBUG [generate_python_code]: No code generated for query: '{last_message.content}'"
                )
                return {"python_code": None}

            print(
                f"DEBUG [generate_python_code]: Query: '{last_message.content}', Code: {python_code}"
            )
            return {"python_code": python_code}

        except Exception as e:
            print(f"ERROR [generate_python_code]: Failed to process query: {str(e)}")
            return {"python_code": None}

    async def execute_python_code(self, state: AppState):
        try:
            python_code = state.get("python_code")
            if not python_code:
                print("DEBUG [execute_python_code]: No Python code to execute")
                return {"execution_result": "No code provided"}

            sandbox = PyodideSandbox(allow_net=True)
            result = await sandbox.execute(python_code)
            print(f"DEBUG [execute_python_code]: Execution result: {result}")
            return {"execution_result": result}

        except Exception as e:
            print(f"ERROR [execute_python_code]: Execution failed: {str(e)}")
            return {"execution_result": f"Error: {str(e)}"}

    def build_graph(self, checkpointer):
        builder = StateGraph(AppState)

        # --- Nodes ---- #
        builder.add_node("check_portfolio_query", self.check_portfolio_query)
        builder.add_node("generate_portfolio_data", self.generate_portfolio_data)
        builder.add_node("check_knowledge_base_query", self.check_knowledge_base_query)
        builder.add_node("search_knowledge_base", self.search_knowledge_base)
        builder.add_node("check_python_code_needed", self.check_python_code_needed)
        builder.add_node(
            "generate_python_code_context", self.generate_python_code_context
        )
        builder.add_node("generate_python_code", self.generate_python_code)
        builder.add_node("execute_python_code", self.execute_python_code)
        builder.add_node("determine_search_need", self.determine_search_need)
        builder.add_node("generate_multiple_queries", self.generate_multiple_queries)
        builder.add_node("search_web", self.search_web)
        builder.add_node("evaluate_search_results", self.evaluate_search_results)
        builder.add_node("call_model", self.call_model)
        builder.add_node("generate_summary", self.generate_summary)
        builder.add_node("tool_node", self.tool_node)

        # --- Edges ---- #
        builder.add_edge(START, "check_portfolio_query")
        builder.add_conditional_edges(
            "check_portfolio_query",
            lambda state: state.get("needs_portfolio", False),
            {True: "generate_portfolio_data", False: "check_knowledge_base_query"},
        )

        builder.add_edge("generate_portfolio_data", "check_knowledge_base_query")
        builder.add_conditional_edges(
            "check_knowledge_base_query",
            lambda state: state.get("needs_knowledge_base", False),
            {True: "search_knowledge_base", False: "check_python_code_needed"},
        )
        builder.add_edge("search_knowledge_base", "check_python_code_needed")
        builder.add_conditional_edges(
            "check_python_code_needed",
            lambda state: state.get("needs_python_code", False),
            {True: "generate_python_code_context", False: "determine_search_need"},
        )
        builder.add_edge("generate_python_code_context", "generate_python_code")
        builder.add_edge("generate_python_code", "execute_python_code")
        builder.add_edge("execute_python_code", "determine_search_need")

        builder.add_conditional_edges(
            "determine_search_need",
            lambda state: state.get("needs_web_search", False),
            {
                True: "generate_multiple_queries",
                False: "call_model",
            },
        )

        builder.add_edge("generate_multiple_queries", "search_web")
        builder.add_edge("search_web", "evaluate_search_results")
        builder.add_conditional_edges(
            "evaluate_search_results",
            lambda state: state.get("search_sufficient", False),
            {
                True: "call_model",
                False: "call_model",
            },
        )

        def route_after_model_call(state: AppState):
            """
            Decide what to do after the LLM has been called.
            If the model decided to use a tool, route to the tool_node.
            Otherwise, the model has produced a final answer, so generate a summary.
            """
            last_message = state["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tool_node"
            else:
                return "generate_summary"

        builder.add_conditional_edges(
            "call_model",
            route_after_model_call,
            {"tool_node": "tool_node", "generate_summary": "generate_summary"},
        )

        builder.add_edge("tool_node", "call_model")

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
                "search_api": "googlesearch",
                "number_of_queries": 1,
                "max_search_depth": 1,
            }
        )
        input_state = {"messages": [HumanMessage(content=user_input)]}
        yielded_contents = set()
        async for state_update_values in self.graph.astream(
            input_state, config, stream_mode="values"
        ):
            last_message = state_update_values["messages"][-1]
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
                if content and content not in yielded_contents:
                    yielded_contents.add(content)
                    yield content


if __name__ == "__main__":
    import asyncio

    GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash	", api_key=GEMINI_API_KEY)

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
