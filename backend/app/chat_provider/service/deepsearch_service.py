import os
from typing import AsyncGenerator, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.chat_provider.service.deepsearch_service_prompt import (
    query_writer_instructions,
    report_planner_query_writer_instructions,
    report_planner_instructions,
    section_writer_inputs,
    final_section_writer_instructions,
    section_grader_instructions,
    section_writer_instructions,
)
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
    get_stock_percentage_change,
    get_stock_point_change,
    get_stock_previous_close,
    get_stock_price_change,
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
from app.chat_provider.tools.news_tools import (
    fetch_finance_news,
    yahoo_finance_news_tool,
    duckduckgo_news_search_tool,
)
from app.chat_provider.tools.basic_tools import (
    get_current_datetime,
    youtube_search_tool,
    python_sandbox_tool,
)
from app.chat_provider.models.deepsearch_models import (
    Feedback,
    Queries,
    ReportState,
    ReportStateInput,
    ReportStateOutput,
    SectionOutputState,
    SectionState,
    Sections,
)
from app.chat_provider.service.deepsearch_utils import (
    format_sections,
    get_config_value,
    get_search_params,
    select_and_execute_search,
)
from app.chat_provider.service.deepsearch_configuration import (
    DEFAULT_REPORT_STRUCTURE,
    Configuration,
)
from langgraph.types import interrupt, Command
from langgraph.types import Send
from dotenv import load_dotenv
import os

load_dotenv()

TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]


class DeepSearchChatService:
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
            get_stock_point_change,
            get_stock_percentage_change,
            get_stock_price_change,
            google_search_tool,
            brave_search_tool,
            duckduckgo_search_results_tool,
            duckduckgo_search_run_tool,
            fetch_finance_news,
            yahoo_finance_news_tool,
            duckduckgo_news_search_tool,
            get_current_datetime,
            youtube_search_tool,
            python_sandbox_tool,
        ]
        # Tool Node
        self.tool_node = ToolNode(self.tools)
        # Bind tools to the model
        self.bound_llm = self.model.bind_tools(self.tools)

    async def call_model(self, state: MessagesState):
        """Call the model with tools and handle tool calls."""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        try:
            response = await self.bound_llm.ainvoke(messages)
            # Ensure response is added to existing messages
            updated_messages = messages + [response]
            return {"messages": updated_messages}
        except Exception as e:
            # Return error message as AIMessage
            error_response = AIMessage(content=f"Error calling model: {str(e)}")
            updated_messages = messages + [error_response]
            return {"messages": updated_messages}

    async def gather_data_with_tools(self, state: SectionState, config: RunnableConfig):
        """Use tools to gather additional data for the section."""
        topic = state["topic"]
        section = state["section"]

        try:
            # Create a prompt that encourages tool usage
            tool_gathering_prompt = f"""
            You are researching the topic: {topic}
            Specifically focusing on: {section.name} - {section.description}
            
            Use the available tools to gather relevant data. For financial topics, use stock tools.
            For current information, use search and news tools.
            
            Please gather comprehensive data using the appropriate tools.
            """

            # Create a messages state for tool calling
            messages = [
                SystemMessage(content=tool_gathering_prompt),
                HumanMessage(content=f"Gather data for: {section.description}"),
            ]

            # Use a simple messages-based approach for tool calling
            tool_state = {"messages": messages}

            # Call model which may trigger tools
            response = await self.call_model(tool_state)
            updated_messages = response.get("messages", [])

            # Check if tools were called in the latest response
            if updated_messages and isinstance(updated_messages[-1], AIMessage):
                last_msg = updated_messages[-1]
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    # Execute tools
                    tool_state["messages"] = updated_messages
                    tool_response = await self.tool_node.ainvoke(tool_state)

                    # Get the tool results
                    tool_messages = tool_response.get("messages", [])

                    # Create a summary of tool results
                    tool_results = []
                    for msg in tool_messages:
                        if hasattr(msg, "content") and msg.content:
                            tool_name = getattr(msg, "name", "Unknown Tool")
                            tool_results.append(
                                f"Tool: {tool_name}\nResult: {msg.content}"
                            )

                    tool_summary = "\n\n".join(tool_results) if tool_results else ""
                    return {"tool_data": tool_summary}

            return {"tool_data": ""}

        except Exception as e:
            # Return empty tool data on error, but log the error
            print(f"Error in gather_data_with_tools: {str(e)}")
            return {"tool_data": ""}

    async def generate_report_plan(self, state: ReportState, config: RunnableConfig):
        """Generate the initial report plan with sections."""
        # Inputs
        topic = state["topic"]

        # Get list of feedback on the report plan
        feedback_list = state.get("feedback_on_report_plan", [])

        # Concatenate feedback on the report plan into a single string
        feedback = " /// ".join(feedback_list) if feedback_list else ""

        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        report_structure = DEFAULT_REPORT_STRUCTURE
        number_of_queries = 5
        search_api = get_config_value(configurable.search_api)
        search_api_config = configurable.search_api_config or {}
        params_to_pass = get_search_params(search_api, search_api_config)

        # Convert JSON object to string if necessary
        if isinstance(report_structure, dict):
            report_structure = str(report_structure)

        structured_llm = self.model.with_structured_output(Queries)

        # Format system instructions
        system_instructions_query = report_planner_query_writer_instructions.format(
            topic=topic,
            report_organization=report_structure,
            number_of_queries=number_of_queries,
        )

        # Generate queries
        results = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions_query),
                HumanMessage(
                    content="Generate search queries that will help with planning the sections of the report."
                ),
            ]
        )

        if isinstance(results, Queries):
            result = results

        # Web search
        query_list = [
            query.search_query
            for query in result.queries
            if query.search_query is not None
        ]

        # Search the web with parameters
        source_str = await select_and_execute_search(
            search_api, query_list, params_to_pass
        )

        # Format system instructions
        system_instructions_sections = report_planner_instructions.format(
            topic=topic,
            report_organization=report_structure,
            context=source_str,
            feedback=feedback,
        )

        # Report planner instructions
        planner_message = """Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. 
                            Each section must have: name, description, research, and content fields."""

        # Generate the report sections
        structured_llm = self.model.with_structured_output(Sections)
        report_sections = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions_sections),
                HumanMessage(content=planner_message),
            ]
        )

        if isinstance(report_sections, Sections):
            report_section = report_sections

        # Get sections
        sections = report_section.sections

        return {"sections": sections}

    async def generate_search_queries(self, state: MessagesState):
        number_of_queries = 4
        structured_llm = self.model.with_structured_output(Queries)
        custom_system_instruction = query_writer_instructions.format(
            number_of_queries=number_of_queries
        )
        result = await structured_llm.ainvoke(
            [
                SystemMessage(content=custom_system_instruction),
                HumanMessage(content="Generate search queries of the provided topic."),
            ]
        )
        if isinstance(result, Queries):
            queries = result
        return {"search_queries": queries.queries}

    def should_continue(self, state: MessagesState):
        """Determine whether to continue with tool calls or end."""
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls"):
            if last_message.tool_calls:
                return "tools"
        return END

    async def generate_queries(self, state: SectionState, config: RunnableConfig):
        """Generate search queries for researching a specific section."""
        # Get state
        topic = state["topic"]
        section = state["section"]

        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        number_of_queries = configurable.number_of_queries
        structured_llm = self.model.with_structured_output(Queries)

        # Format system instructions
        system_instructions = query_writer_instructions.format(
            topic=topic,
            section_topic=section.description,
            number_of_queries=number_of_queries,
        )

        # Generate queries
        queries = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate search queries on the provided topic."),
            ]
        )
        if isinstance(queries, Queries):
            return {"search_queries": queries.queries}

    async def search_web(self, state: SectionState, config: RunnableConfig):
        """Execute web searches for the section queries."""
        search_queries = state["search_queries"]

        configurable = Configuration.from_runnable_config(config)
        search_api = get_config_value(configurable.search_api)
        search_api_config = configurable.search_api_config or {}
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
            "search_iterations": state["search_iterations"] + 1,
        }

    async def write_section(self, state: SectionState, config: RunnableConfig):
        topic = state["topic"]
        section = state["section"]
        source_str = state["source_str"]
        tool_data = state.get("tool_data", "")
        configurable = Configuration.from_runnable_config(config)

        # Enhanced section writing with tool data
        enhanced_context = (
            f"{source_str}\n\nAdditional Tool Data:\n{tool_data}"
            if tool_data
            else source_str
        )

        section_writer_inputs_formatted = section_writer_inputs.format(
            topic=topic,
            section_name=section.name,
            section_topic=section.description,
            context=enhanced_context,
            section_content=section.content,
        )

        section_content = await self.model.ainvoke(
            [
                SystemMessage(content=section_writer_instructions),
                HumanMessage(content=section_writer_inputs_formatted),
            ]
        )

        section.content = section_content.content

        section_grader_instructions_formatted = section_grader_instructions.format(
            topic=topic,
            section_topic=section.description,
            section=section.content,
            number_of_follow_up_queries=configurable.number_of_queries,
        )
        reflection_model = self.model.with_structured_output(Feedback)
        feedback = await reflection_model.ainvoke(
            [
                SystemMessage(content=section_grader_instructions_formatted),
                HumanMessage(
                    content="Grade the report and provide follow-up queries if needed."
                ),
            ]
        )
        if not isinstance(feedback, Feedback):
            return

        if (
            feedback.grade == "pass"
            or state["search_iterations"] >= configurable.max_search_depth
        ):
            return {"completed_sections": [section]}
        else:
            return {
                "search_queries": feedback.follow_up_queries,
                "section": section,
                "search_iterations": state["search_iterations"] + 1,
            }

    async def write_final_sections(self, state: SectionState, config: RunnableConfig):
        """Write sections that don't require research using completed sections as context."""
        # Get state
        topic = state["topic"]
        section = state["section"]
        completed_report_sections = state["report_sections_from_research"]

        # Format system instructions
        system_instructions = final_section_writer_instructions.format(
            topic=topic,
            section_name=section.name,
            section_topic=section.description,
            context=completed_report_sections,
        )

        section_content = await self.bound_llm.ainvoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(
                    content="Generate a report section based on the provided sources."
                ),
            ]
        )

        # Write content to section
        section.content = section_content.content

        # Write the updated section to completed sections
        return {"completed_sections": [section]}

    def gather_completed_sections(self, state: ReportState):
        """Format completed sections as context for writing final sections."""
        # List of completed sections
        completed_sections = state["completed_sections"]

        # Format completed section to str to use as context for final sections
        completed_report_sections = format_sections(completed_sections)

        return {"report_sections_from_research": completed_report_sections}

    def compile_final_report(self, state: ReportState):
        """Compile all sections into the final report."""
        # Get sections
        sections = state["sections"]
        completed_sections = {s.name: s.content for s in state["completed_sections"]}

        # Update sections with completed content while maintaining original order
        for section in sections:
            section.content = completed_sections[section.name]

        # Compile final report
        all_sections = "\n\n".join([s.content for s in sections])

        return {"final_report": all_sections}

    def initiate_final_section_writing(self, state: ReportState):
        """Create parallel tasks for writing non-research sections."""
        # Kick off section writing in parallel via Send() API for any sections that do not require research
        return [
            Send(
                "write_final_sections",
                {
                    "topic": state["topic"],
                    "section": s,
                    "report_sections_from_research": state[
                        "report_sections_from_research"
                    ],
                },
            )
            for s in state["sections"]
            if not s.research
        ]

    def dispatch_sections(
        self, state: ReportState
    ) -> Command[Literal["build_section_with_web_research"]]:
        sections = state["sections"]
        topic = state["topic"]
        return Command(
            goto=[
                Send(
                    "build_section_with_web_research",
                    {
                        "topic": topic,
                        "section": s,
                        "search_queries": [],
                        "source_str": "",
                        "tool_data": "",  # Add tool_data field
                        "search_iterations": 0,
                        "completed_sections": None,
                    },
                )
                for s in sections
                if s.research
            ]
        )

    def build_graph(self, checkpointer):
        # Build section builder with tool integration
        section_builder = StateGraph(SectionState, output=SectionOutputState)
        section_builder.add_node("generate_queries", self.generate_queries)
        section_builder.add_node("gather_data_with_tools", self.gather_data_with_tools)
        section_builder.add_node("search_web", self.search_web)
        section_builder.add_node("write_section", self.write_section)

        section_builder.add_edge(START, "generate_queries")
        section_builder.add_edge("generate_queries", "gather_data_with_tools")
        section_builder.add_edge("gather_data_with_tools", "search_web")
        section_builder.add_edge("search_web", "write_section")
        section_builder.add_conditional_edges(
            "write_section",
            lambda state: END
            if state.get("completed_sections")
            else "gather_data_with_tools",
            {"gather_data_with_tools": "gather_data_with_tools", END: END},
        )

        # Main graph
        builder = StateGraph(
            ReportState,
            input=ReportStateInput,
            output=ReportStateOutput,
            config_schema=Configuration,
        )
        builder.add_node("tools", self.tool_node)
        builder.add_node("generate_report_plan", self.generate_report_plan)
        builder.add_node("dispatch_sections", self.dispatch_sections)
        builder.add_node("build_section_with_web_research", section_builder.compile())
        builder.add_node("gather_completed_sections", self.gather_completed_sections)
        builder.add_node("write_final_sections", self.write_final_sections)
        builder.add_node("compile_final_report", self.compile_final_report)

        builder.add_edge(START, "generate_report_plan")
        builder.add_edge("generate_report_plan", "dispatch_sections")
        builder.add_edge("build_section_with_web_research", "gather_completed_sections")
        builder.add_conditional_edges(
            "gather_completed_sections",
            self.initiate_final_section_writing,
            ["write_final_sections"],
        )
        builder.add_edge("write_final_sections", "compile_final_report")
        builder.add_edge("compile_final_report", END)
        self.graph = builder.compile(checkpointer=checkpointer)
        return self.graph

    async def stream_input(
        self, user_input: str, thread_id: str, user_id: str = "", session_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """Stream the model's response to user input asynchronously."""
        config = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "search_api": "googlesearch",
                "number_of_queries": 2,
                "max_search_depth": 2,
                # "search_api_config": {"api_key": TAVILY_API_KEY},
            }
        )
        # Construct a valid ReportState
        input_state = {
            "topic": user_input,
            "feedback_on_report_plan": [],
            "sections": [],
            "completed_sections": [],
            "report_sections_from_research": "",
            "final_report": "",
        }

        # Track if we've yielded anything
        has_yielded = False

        try:
            async for state_update in self.graph.astream(
                input_state, config, stream_mode="values"
            ):
                # Priority 1: Check if final_report is available
                if "final_report" in state_update and state_update["final_report"]:
                    yield state_update["final_report"]
                    has_yielded = True
                    break  # Final report is complete, no need to continue

                # Priority 2: Check for sections being completed
                elif "sections" in state_update and state_update["sections"]:
                    sections_summary = f"Generated {len(state_update['sections'])} sections for analysis"
                    yield sections_summary
                    has_yielded = True

                # Priority 3: Check for completed sections
                elif (
                    "completed_sections" in state_update
                    and state_update["completed_sections"]
                ):
                    completed_count = len(state_update["completed_sections"])
                    yield f"Completed {completed_count} sections"
                    has_yielded = True

                # Priority 4: Check for progress updates
                elif (
                    "report_sections_from_research" in state_update
                    and state_update["report_sections_from_research"]
                ):
                    yield "Gathering research sections..."
                    has_yielded = True

                # Priority 5: Fallback to messages if they exist and are AI messages
                elif "messages" in state_update and state_update["messages"]:
                    messages = state_update["messages"]
                    if messages and isinstance(messages[-1], AIMessage):
                        last_message = messages[-1]
                        content = last_message.content
                        if isinstance(content, list):
                            content = "\n".join(str(item) for item in content)
                        if content and content.strip():  # Only yield non-empty content
                            yield content
                            has_yielded = True

        except Exception as e:
            error_msg = f"Error during report generation: {str(e)}"
            yield error_msg
            has_yielded = True

        # Ensure we always yield something
        if not has_yielded:
            yield "Report generation started..."


if __name__ == "__main__":
    import asyncio

    async def main():
        # Set USER_AGENT to avoid warning
        os.environ["USER_AGENT"] = (
            "DeepSearchChatService/1.0 (Contact: your-email@example.com)"
        )

        GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
        )

        DB_URI = "postgresql://postgres:postgres@localhost:5434/postgres"
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            chat_service = DeepSearchChatService(model=model)
            chat_service.build_graph(checkpointer)
            thread_id = "1"

            # Test stream_input with a valid topic
            print("\nStreaming responses:")
            async for chunk in chat_service.stream_input(
                "Financial analysis of Apple Inc.", thread_id
            ):
                print(chunk)

    asyncio.run(main())
