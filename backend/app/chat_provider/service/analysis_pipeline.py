# analysis_pipeline.py
def stock_analysis_pipeline(chat_service):
    """
    A comprehensive pipeline for stock analysis that:
    1. Retrieves the full equity list.
    2. Filters stocks based on liquidity and volatility.
    3. Performs in-depth research on top candidates.
    4. Generates a detailed investment report.
    """
    print("Step 1: Retrieving Full Equity List")
    # print(f"Total Equities Found: {len(equity_list)}")
    equity_list = []

    top_candidates = []
    print("\nStep 2: Analyzing Stock Liquidity and Volatility")
    for stock in equity_list[:20]:
        try:
            stock_data = chat_service.chat_tools.get_price_volume_and_deliverable_data(
                {"symbol": stock, "period": "1M"}
            )
            if stock_data:
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

    print("\nStep 3: Comprehensive Stock Research")
    detailed_research = []
    for candidate in top_candidates[:5]:
        stock = candidate["symbol"]
        print(f"\nResearching {stock}")
        web_research = chat_service.comprehensive_stock_research(stock)
        try:
            financial_results = (
                chat_service.chat_tools.get_financial_results_for_equity(
                    {"fin_period": "Quarterly"}
                )
            )
        except Exception as e:
            financial_results = f"Could not fetch financial results: {e}"
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

    print("\nStep 4: Generating Investment Report")
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
            "Stock Price and Basic Information:\n" + stock_price_info
        )
    except Exception as e:
        research_sections.append(f"Stock Price Info Error: {str(e)}")

    # 2. Web Search for Company Overview
    try:
        company_search = self.chat_tools.search_web(
            f"{ticker} company overview", max_results=max_sources
        )
        research_sections.append("\nCompany Overview:\n" + company_search)
    except Exception as e:
        research_sections.append(f"Company Overview Search Error: {str(e)}")

    # 3. Recent News
    try:
        news_search = self.chat_tools.search_web(
            f"{ticker} recent news financial", max_results=max_sources
        )
        research_sections.append(
            "\n📰 Recent News and Market Sentiment:\n" + news_search
        )
    except Exception as e:
        research_sections.append(f"News Search Error: {str(e)}")

    # 4. Financial Performance
    try:
        financial_search = self.chat_tools.search_web(
            f"{ticker} financial performance quarterly results",
            max_results=max_sources,
        )
        research_sections.append("\n Financial Performance:\n" + financial_search)
    except Exception as e:
        research_sections.append(f"Financial Performance Search Error: {str(e)}")

    # 5. Analyst Recommendations
    try:
        analyst_search = self.chat_tools.search_web(
            f"{ticker} analyst recommendations target price",
            max_results=max_sources,
        )
        research_sections.append("\n🔍 Analyst Recommendations:\n" + analyst_search)
    except Exception as e:
        research_sections.append(f"Analyst Recommendations Search Error: {str(e)}")

    # Combine and format the research
    full_research = "\n\n".join(research_sections)

    # Add a comprehensive disclaimer
    disclaimer = (
        "\n\n DISCLAIMER:\n"
        "This research is compiled from web sources and AI analysis. "
        "It is NOT financial advice. Always consult professional financial advisors, "
        "conduct your own due diligence, and be aware that market conditions can change rapidly."
    )

    return full_research + disclaimer
