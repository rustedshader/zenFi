from langchain_core.tools import tool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.tools import (
    DuckDuckGoSearchResults,
)


yahoo_finance_news_tool = YahooFinanceNewsTool()
duckduckgo_news_search_tool = DuckDuckGoSearchResults(backend="news")

if __name__ == "__main__":
    print(yahoo_finance_news_tool.invoke("RELIANCE.NS"))
    print(duckduckgo_news_search_tool.invoke("RELIANCE.NS"))
