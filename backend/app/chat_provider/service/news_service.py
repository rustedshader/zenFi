import os
import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from app.chat_provider.models.news_models import (
    FinanceNewsReport,
    FinanceNewsState,
    SearchQueries,
)
from app.chat_provider.service.deepsearch_configuration import (
    Configuration,
)

from app.chat_provider.service.deepsearch_utils import (
    get_config_value,
    get_search_params,
    select_and_execute_search,
)
from app.chat_provider.service.news_service_prompt import (
    query_writer_instructions,
    topic_specific_query_instructions,
    generate_news_instructions,
)

load_dotenv()

TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]


class FinanceNewsService:
    def __init__(
        self,
        model: ChatGoogleGenerativeAI,
    ):
        self.model = model

    async def generate_queries(self, state: FinanceNewsState):
        topic = state["topic"]
        structured_llm = self.model.with_structured_output(SearchQueries)
        system_instructions = query_writer_instructions.format(
            topic=topic,
        )
        queries = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate search queries on the provided topic."),
            ]
        )

        return {"search_queries": queries.queries}

    async def search_web(self, state: FinanceNewsState, config: RunnableConfig):
        search_queries = state["search_queries"]
        configurable = Configuration.from_runnable_config(config)
        search_api = get_config_value(configurable.search_api)
        search_api_config = configurable.search_api_config or {}
        params_to_pass = get_search_params(search_api, search_api_config)
        source_str = await select_and_execute_search(
            search_api, search_queries, params_to_pass
        )
        return {"search_response": source_str}

    async def generate_topic_specific_financial_queries(self, state: FinanceNewsState):
        search_response = state["search_response"]
        structured_llm = self.model.with_structured_output(SearchQueries)
        system_instructions = topic_specific_query_instructions.format(
            search_response=search_response
        )
        queries = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(
                    content="Generate search queries on the provided top financial news data."
                ),
            ]
        )
        return {"news_search_queries": queries.queries}

    async def search_financial_queries(
        self, state: FinanceNewsState, config: RunnableConfig
    ):
        news_search_queries = state["news_search_queries"]
        configurable = Configuration.from_runnable_config(config)
        search_api = get_config_value(configurable.search_api)
        search_api_config = configurable.search_api_config or {}
        params_to_pass = get_search_params(search_api, search_api_config)
        source_str = await select_and_execute_search(
            search_api, news_search_queries, params_to_pass
        )
        return {"news_search_response": source_str}

    async def generate_news_report(self, state: FinanceNewsState):
        news_search_response = state["news_search_response"]
        structured_llm = self.model.with_structured_output(FinanceNewsReport)

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        system_instructions = generate_news_instructions.format(
            news_search_response=news_search_response, date=current_date
        )

        news_report_wrapper = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(
                    content="Generate a financial news report based on the provided news search response."
                ),
            ]
        )

        return {"news_report": news_report_wrapper.news_items}

    def build_graph(self):
        builder = StateGraph(FinanceNewsState)

        builder.add_node("generate_queries", self.generate_queries)
        builder.add_node("search_web", self.search_web)
        builder.add_node(
            "generate_topic_specific_financial_queries",
            self.generate_topic_specific_financial_queries,
        )
        builder.add_node("search_financial_queries", self.search_financial_queries)
        builder.add_node("generate_news_report", self.generate_news_report)

        builder.add_edge(START, "generate_queries")
        builder.add_edge("generate_queries", "search_web")
        builder.add_edge("search_web", "generate_topic_specific_financial_queries")
        builder.add_edge(
            "generate_topic_specific_financial_queries", "search_financial_queries"
        )
        builder.add_edge("search_financial_queries", "generate_news_report")
        builder.add_edge("generate_news_report", END)

        self.graph = builder.compile()
        return self.graph

    async def get_latest_finance_news(self, graph):
        initial_state = {
            "messages": [HumanMessage(content="Generate top Financial News")],
            "topic": "Top Financial News",
        }
        x = await graph.ainvoke(initial_state)
        response = dict(x)
        if isinstance(response.get("search_queries"), SearchQueries):
            response["search_queries"] = response["search_queries"].dict()
        return response


if __name__ == "__main__":
    import asyncio

    GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
    )

    async def main():
        GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY
        )
        chat_service = FinanceNewsService(model=model)
        graph = chat_service.build_graph()
        x = await chat_service.get_latest_finance_news(graph)
        print(x)

    asyncio.run(main())
