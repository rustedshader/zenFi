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
from app.chat_provider.tools.basic_tools import get_current_datetime
from app.chat_provider.models.chat_models import (
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
        ]
        # Tool Node
        self.tool_node = ToolNode(self.tools)
        # Set the system prompt
        # Bind tools to the model
        self.bound_llm = self.model.bind_tools(self.tools)

    # async def call_model(self, state: MessagesState):
    #     messages =  state["messages"]
    #     response = await self.bound_llm.ainvoke(messages)
    #     return {"messages": response}

    async def generate_report_plan(self, state: ReportState, config: RunnableConfig):
        """Generate the initial report plan with sections.

        This node:
        1. Gets configuration for the report structure and search parameters
        2. Generates search queries to gather context for planning
        3. Performs web searches using those queries
        4. Uses an LLM to generate a structured plan with sections

        Args:
            state: Current graph state containing the report topic
            config: Configuration for models, search APIs, etc.

        Returns:
            Dict containing the generated sections
        """

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
        search_api_config = (
            configurable.search_api_config or {}
        )  # Get the config dict, default to empty
        params_to_pass = get_search_params(
            search_api, search_api_config
        )  # Filter parameters

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
        # TODO: Complete This
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
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            if last_message.tool_calls:
                return "tools"
        else:
            print("Error: Last Message Instance is not AIMessage")
        return END

    async def generate_queries(self, state: SectionState, config: RunnableConfig):
        """Generate search queries for researching a specific section.

        This node uses an LLM to generate targeted search queries based on the
        section topic and description.

        Args:
            state: Current state containing section details
            config: Configuration including number of queries to generate

        Returns:
            Dict containing the generated search queries
        """

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
        """Execute web searches for the section queries.

        This node:
        1. Takes the generated queries
        2. Executes searches using configured search API
        3. Formats results into usable context

        Args:
            state: Current state with search queries
            config: Search API configuration

        Returns:
            Dict with search results and updated iteration count
        """

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
        configurable = Configuration.from_runnable_config(config)

        section_writer_inputs_formatted = section_writer_inputs.format(
            topic=topic,
            section_name=section.name,
            section_topic=section.description,
            context=source_str,
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
            return {"completed_sections": [section]}  # Wrap section in a list
        else:
            return {
                "search_queries": feedback.follow_up_queries,
                "section": section,
                "search_iterations": state["search_iterations"] + 1,
            }

    async def write_final_sections(self, state: SectionState, config: RunnableConfig):
        """Write sections that don't require research using completed sections as context.

        This node handles sections like conclusions or summaries that build on
        the researched sections rather than requiring direct research.

        Args:
            state: Current state with completed sections as context
            config: Configuration for the writing model

        Returns:
            Dict containing the newly written section
        """

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

    async def human_feedback(
        self, state: ReportState, config: RunnableConfig
    ) -> Command[Literal["generate_report_plan", "build_section_with_web_research"]]:
        """Get human feedback on the report plan and route to next steps.

        This node:
        1. Formats the current report plan for human review
        2. Gets feedback via an interrupt
        3. Routes to either:
        - Section writing if plan is approved
        - Plan regeneration if feedback is provided

        Args:
            state: Current graph state with sections to review
            config: Configuration for the workflow

        Returns:
            Command to either regenerate plan or start section writing
        """

        # Get sections
        topic = state["topic"]
        sections = state["sections"]
        sections_str = "\n\n".join(
            f"Section: {section.name}\n"
            f"Description: {section.description}\n"
            f"Research needed: {'Yes' if section.research else 'No'}\n"
            for section in sections
        )

        # Get feedback on the report plan from interrupt
        interrupt_message = f"""Please provide feedback on the following report plan. 
                            \n\n{sections_str}\n
                            \nDoes the report plan meet your needs?\nPass 'true' to approve the report plan.\nOr, provide feedback to regenerate the report plan:"""

        feedback = interrupt(interrupt_message)

        # If the user approves the report plan, kick off section writing
        if isinstance(feedback, bool) and feedback is True:
            # Treat this as approve and kick off section writing
            return Command(
                goto=[
                    Send(
                        "build_section_with_web_research",
                        {"topic": topic, "section": s, "search_iterations": 0},
                    )
                    for s in sections
                    if s.research
                ]
            )

        # If the user provides feedback, regenerate the report plan
        elif isinstance(feedback, str):
            # Treat this as feedback and append it to the existing list
            return Command(
                goto="generate_report_plan",
                update={"feedback_on_report_plan": [feedback]},
            )
        else:
            raise TypeError(
                f"Interrupt value of type {type(feedback)} is not supported."
            )

    def gather_completed_sections(self, state: ReportState):
        """Format completed sections as context for writing final sections.

        This node takes all completed research sections and formats them into
        a single context string for writing summary sections.

        Args:
            state: Current state with completed sections

        Returns:
            Dict with formatted sections as context
        """

        # List of completed sections
        completed_sections = state["completed_sections"]

        # Format completed section to str to use as context for final sections
        completed_report_sections = format_sections(completed_sections)

        return {"report_sections_from_research": completed_report_sections}

    def compile_final_report(self, state: ReportState):
        """Compile all sections into the final report.

        This node:
        1. Gets all completed sections
        2. Orders them according to original plan
        3. Combines them into the final report

        Args:
            state: Current state with all completed sections

        Returns:
            Dict containing the complete report
        """

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
        """Create parallel tasks for writing non-research sections.

        This edge function identifies sections that don't need research and
        creates parallel writing tasks for each one.

        Args:
            state: Current state with all sections and research context

        Returns:
            List of Send commands for parallel section writing
        """

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
                        "search_iterations": 0,
                        "completed_sections": None,
                    },
                )
                for s in sections
                if s.research
            ]
        )

    def build_graph(self, checkpointer):
        # https://langchain-ai.github.io/langgraph/how-tos/tool-calling/#use-prebuilt-toolnode
        # Reference: https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/graph.py

        section_builder = StateGraph(SectionState, output=SectionOutputState)
        section_builder.add_node("generate_queries", self.generate_queries)
        section_builder.add_node("search_web", self.search_web)
        section_builder.add_node("write_section", self.write_section)
        section_builder.add_edge(START, "generate_queries")
        section_builder.add_edge("generate_queries", "search_web")
        section_builder.add_edge("search_web", "write_section")
        section_builder.add_conditional_edges(
            "write_section",
            lambda state: END if state.get("completed_sections") else "search_web",
            {"search_web": "search_web", END: END},
        )

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
        self, user_input: str, thread_id: str, user_id: str, session_id: str
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
            "topic": user_input,  # Use user_input as the topic
            "feedback_on_report_plan": [],
            "sections": [],
            "completed_sections": [],
            "report_sections_from_research": "",
            "final_report": "",
        }
        async for state_update in self.graph.astream(
            input_state, config, stream_mode="values"
        ):
            # Check if final_report is available in the state
            if "final_report" in state_update and state_update["final_report"]:
                yield state_update["final_report"]
            # Fallback to messages if final_report is not yet available
            elif "messages" in state_update and state_update["messages"]:
                last_message = state_update["messages"][-1]
                if isinstance(last_message, AIMessage):
                    content = last_message.content
                    if isinstance(content, list):
                        content = "\n".join(str(item) for item in content)
                    yield content


if __name__ == "__main__":
    import asyncio

    GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
    )

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
