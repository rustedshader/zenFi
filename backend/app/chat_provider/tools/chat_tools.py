import time
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import WikipediaLoader
from langchain_community.utilities import SearxSearchWrapper
from langchain_community.tools import BraveSearch
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.tools import YouTubeSearchTool
from nselib.capital_market import (
    price_volume_and_deliverable_position_data,
    index_data,
    bhav_copy_with_delivery,
    equity_list,
    fno_equity_list,
    market_watch_all_indices,
    financial_results_for_equity,
)
from nselib.derivatives import (
    future_price_volume_data,
    option_price_volume_data,
    fno_bhav_copy,
    participant_wise_open_interest,
    participant_wise_trading_volume,
    fii_derivatives_statistics,
    expiry_dates_future,
    expiry_dates_option_index,
    nse_live_option_chain,
)
import yfinance as yf
from langchain_community.document_loaders import YoutubeLoader

from mftool import Mftool


class ChatTools:
    def __init__(
        self,
        duckduckgo_general: DuckDuckGoSearchResults = None,
        duckduckgo_news: DuckDuckGoSearchResults = None,
        searxng: SearxSearchWrapper = None,
        brave_search: BraveSearch = None,
        youtube_search: YouTubeSearchTool = None,
    ):
        self.duckduckgo_general = duckduckgo_general
        self.duckduckgo_news = duckduckgo_news
        self.searxng = searxng
        self.brave_search = brave_search
        self.youtube_search = youtube_search
        self.youtube_captioner = YouTubeSearchTool

        # Initialize mftool for mutual funds data
        self.mftool = Mftool()

    def _mftool_retry(self, func, *args, retries=3, delay=5, **kwargs):
        """
        Helper method to retry mftool calls in case of transient errors.
        """
        last_exception = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                time.sleep(delay)
        raise last_exception

    def get_youtube_captions(self, video_ids: list[str]):
        """Retrieve captions and video info for a list of YouTube video IDs."""
        if not self.youtube_captioner:
            return "YouTube captioner tool not initialized."

        if not video_ids:
            return "No video IDs provided."

        # Update video_ids in the youtube_captioner instance
        self.youtube_captioner.video_ids = video_ids

        try:
            results = []
            for video_id in video_ids:
                loader = YoutubeLoader.from_youtube_url(
                    f"https://www.youtube.com/watch?v={video_id}",
                    add_video_info=False,
                    language=["en"],
                )
                video_data = loader.load()
                if video_data:
                    results.extend(video_data)

            if results:
                return "\n".join([str(result) for result in results])
            return "No captions or data found for the provided video IDs."

        except Exception as e:
            return f"Error retrieving YouTube captions: {str(e)}"

    def search_wikipedia(self, query: str):
        """Search Wikipedia and return the content of the first matching page."""
        docs = WikipediaLoader(query=query, load_max_docs=2).load()
        return docs[0].page_content if docs else "No results found."

    def search_searxng(self, query: str):
        """Search using SearxNG and return the results."""
        if self.searxng:
            return self.searxng.run(query)
        return "SearxNG search tool not initialized."

    def search_brave(self, query: str):
        """Search using Brave Search and return the results."""
        if self.brave_search:
            return self.brave_search.run(query)
        return "Brave Search tool not initialized."

    def search_youtube(self, query: str):
        """Search YouTube and return results as a formatted string."""
        if self.youtube_search:
            results = self.youtube_search.run(query)
            if isinstance(results, list):
                return "\n".join([str(result) for result in results])
            return str(results)
        return "Youtube Search tool not initialized"

    def search_duckduckgo(
        self, query: str, backend: str = "general", output_format: str = None
    ):
        """
        Search using DuckDuckGo with specified backend and output format.
        Args:
            query (str): The search query.
            backend (str): "general" or "news" to select the search backend (default: "general").
            output_format (str): "list" to return results as a list, None for a string (default: None).
        Returns:
            Results as a list or formatted string based on output_format.
        """
        if backend == "general" and self.duckduckgo_general:
            search_tool = self.duckduckgo_general
        elif backend == "news" and self.duckduckgo_news:
            search_tool = self.duckduckgo_news
        else:
            return f"Invalid backend: {backend} or tool not initialized."

        results = search_tool.invoke(query)
        if output_format == "list":
            return results
        else:
            if isinstance(results, list):
                return "\n".join([str(result) for result in results])
            return str(results)

    def search_web(self, query: str, max_results: int = 5):
        """
        Search the web using multiple search engines and combine results.

        Args:
            query (str): The search query.
            max_results (int): Maximum number of results to return from each search engine (default: 5).

        Returns:
            str: Combined search results from different search engines.
        """
        # Initialize results list
        combined_results = []

        # Search SearxNG
        try:
            if self.searxng:
                searxng_results = self.searxng.run(query)
                if isinstance(searxng_results, list):
                    combined_results.extend(searxng_results)
                else:
                    combined_results.append(searxng_results)
        except Exception as e:
            combined_results.append(f"SearxNG Search Error: {str(e)}")

        # Search Brave
        try:
            if self.brave_search:
                brave_results = self.brave_search.run(query)
                if isinstance(brave_results, list):
                    combined_results.extend(brave_results)
                else:
                    combined_results.append(brave_results)
        except Exception as e:
            combined_results.append(f"Brave Search Error: {str(e)}")

        # Search DuckDuckGo (general)
        try:
            if self.duckduckgo_general:
                ddg_results = self.search_duckduckgo(query)
                if isinstance(ddg_results, list):
                    combined_results.extend(ddg_results)
                else:
                    combined_results.append(ddg_results)
        except Exception as e:
            combined_results.append(f"DuckDuckGo Search Error: {str(e)}")

        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in combined_results:
            result_str = str(result)
            if result_str not in seen:
                seen.add(result_str)
                unique_results.append(result)

        # Return results as a formatted string
        if unique_results:
            return "\n\n".join([str(result) for result in unique_results])
        else:
            return "No search results found."

    def scrape_web_url(self, url: str) -> str:
        """
        Scrape content from a given URL.

        Args:
            url (str): The URL to scrape.

        Returns:
            str: The scraped content or error message.
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return "Error: Invalid URL. Must start with http:// or https://"

            # Load and parse the URL
            loader = WebBaseLoader(url)
            docs = loader.load()

            # Check if any content was retrieved
            if not docs:
                return "Error: No content found at the URL"

            return docs[0].page_content

        except ValueError as e:
            return f"URL Error: {str(e)}"
        except Exception as e:
            return f"Error scraping URL {url}: {str(e)}"

    def get_stock_prices(self, symbol: str):
        """
        Retrieve stock information for the given symbol using yfinance.
        Args:
            symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
        Returns:
            str: Formatted string with stock details or an error message.
        """
        try:
            dat = yf.Ticker(symbol)
            info = dat.info
            return (
                f"Company Name: {info.get('longName', 'N/A')}\n"
                f"Current Price: {info.get('currentPrice', 'N/A')}\n"
                f"Previous Close: {info.get('previousClose', 'N/A')}\n"
                f"Market Cap: {info.get('marketCap', 'N/A')}"
            )
        except Exception as e:
            return f"Error retrieving stock information for {symbol}: {str(e)}"

    # New NSE data methods
    def get_price_volume_and_deliverable_data(
        self,
        symbol: str,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
    ):
        """Retrieve price, volume, and deliverable position data for a stock."""
        try:
            df = price_volume_and_deliverable_position_data(
                symbol, from_date, to_date, period
            )
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving price, volume, and deliverable data: {str(e)}"

    def get_index_data(
        self, index: str, from_date: str = None, to_date: str = None, period: str = None
    ):
        """Retrieve historical data for an NSE index."""
        try:
            df = index_data(index, from_date, to_date, period)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving index data: {str(e)}"

    def get_bhav_copy_with_delivery(self, trade_date: str):
        """Retrieve bhav copy with delivery data for a specific trade date."""
        try:
            df = bhav_copy_with_delivery(trade_date)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving bhav copy with delivery: {str(e)}"

    def get_equity_list(self):
        """Retrieve the list of all equities available to trade on NSE."""
        try:
            df = equity_list()
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving equity list: {str(e)}"

    def get_fno_equity_list(self):
        """Retrieve the list of derivative equities with lot sizes."""
        try:
            df = fno_equity_list()
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving F&O equity list: {str(e)}"

    def get_market_watch_all_indices(self):
        """Retrieve market watch data for all NSE indices."""
        try:
            df = market_watch_all_indices()
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving market watch data: {str(e)}"

    def get_financial_results_for_equity(
        self,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
        fo_sec: bool = None,
        fin_period: str = "Quarterly",
    ):
        """Retrieve financial results for equities."""
        try:
            df = financial_results_for_equity(
                from_date, to_date, period, fo_sec, fin_period
            )
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving financial results: {str(e)}"

    def get_future_price_volume_data(
        self,
        symbol: str,
        instrument: str,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
    ):
        """Retrieve future price volume data for a given symbol and instrument."""
        try:
            df = future_price_volume_data(
                symbol, instrument, from_date, to_date, period
            )
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving future price volume data: {str(e)}"

    def get_option_price_volume_data(
        self,
        symbol: str,
        instrument: str,
        option_type: str = None,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
    ):
        """Retrieve option price volume data for a given symbol, instrument, and option type."""
        try:
            df = option_price_volume_data(
                symbol, instrument, option_type, from_date, to_date, period
            )
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving option price volume data: {str(e)}"

    def get_fno_bhav_copy(self, trade_date: str):
        """Retrieve F&O bhav copy for a specific trade date."""
        try:
            df = fno_bhav_copy(trade_date)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving F&O bhav copy: {str(e)}"

    def get_participant_wise_open_interest(self, trade_date: str):
        """Retrieve participant-wise open interest data for a specific trade date."""
        try:
            df = participant_wise_open_interest(trade_date)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving participant-wise open interest: {str(e)}"

    def get_participant_wise_trading_volume(self, trade_date: str):
        """Retrieve participant-wise trading volume data for a specific trade date."""
        try:
            df = participant_wise_trading_volume(trade_date)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving participant-wise trading volume: {str(e)}"

    def get_fii_derivatives_statistics(self, trade_date: str):
        """Retrieve FII derivatives statistics for a specific trade date."""
        try:
            df = fii_derivatives_statistics(trade_date)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving FII derivatives statistics: {str(e)}"

    def get_expiry_dates_future(self):
        """Retrieve future and option expiry dates."""
        try:
            dates = expiry_dates_future()
            return ", ".join(dates)
        except Exception as e:
            return f"Error retrieving future expiry dates: {str(e)}"

    def get_expiry_dates_option_index(self):
        """Retrieve expiry dates for option indices."""
        try:
            data = expiry_dates_option_index()
            return str(data)  # Return dictionary as string
        except Exception as e:
            return f"Error retrieving option index expiry dates: {str(e)}"

    def get_nse_live_option_chain(
        self, symbol: str, expiry_date: str = None, oi_mode: str = "full"
    ):
        """Retrieve live NSE option chain for a given symbol and expiry date."""
        try:
            df = nse_live_option_chain(symbol, expiry_date, oi_mode)
            return df.to_string(index=False)
        except Exception as e:
            return f"Error retrieving live option chain: {str(e)}"

    # -------------------------------
    # New Methods for mftool (Mutual Funds Data)
    # -------------------------------

    def get_mf_available_schemes(self, amc: str):
        """
        Retrieve all available schemes for a given AMC.
        Args:
            amc (str): The AMC name (e.g., 'ICICI').
        Returns:
            str: A string representation of the available schemes dictionary.
        """
        try:
            result = self._mftool_retry(self.mftool.get_available_schemes, amc)
            return str(result)
        except Exception as e:
            return f"Error retrieving available schemes for {amc}: {str(e)}"

    def get_mf_quote(self, scheme_code, as_json: bool = False):
        """
        Retrieve the latest quote for a given mutual fund scheme.
        Args:
            scheme_code (str/int): The scheme code.
            as_json (bool): If True, return the result in JSON format.
        Returns:
            str: The scheme quote data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_scheme_quote, str(scheme_code), as_json=as_json
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving scheme quote for {scheme_code}: {str(e)}"

    def get_mf_details(self, scheme_code, as_json: bool = False):
        """
        Retrieve scheme details for a given mutual fund scheme.
        Args:
            scheme_code (str/int): The scheme code.
            as_json (bool): If True, return the result in JSON format.
        Returns:
            str: The scheme details.
        """
        try:
            if as_json:
                result = self._mftool_retry(
                    self.mftool.get_scheme_info, str(scheme_code), as_json=True
                )
            else:
                result = self._mftool_retry(
                    self.mftool.get_scheme_details, str(scheme_code)
                )
            return str(result)
        except Exception as e:
            return f"Error retrieving scheme details for {scheme_code}: {str(e)}"

    def get_mf_codes(self, as_json: bool = False):
        """
        Retrieve a dictionary of all mutual fund scheme codes and their names.
        Args:
            as_json (bool): If True, return the result in JSON format.
        Returns:
            str: The scheme codes dictionary.
        """
        try:
            result = self._mftool_retry(self.mftool.get_scheme_codes, as_json=as_json)
            return str(result)
        except Exception as e:
            return f"Error retrieving scheme codes: {str(e)}"

    def get_mf_historical_nav(
        self, scheme_code, as_json: bool = False, as_dataframe: bool = False
    ):
        """
        Retrieve historical NAV data for a given scheme.
        Args:
            scheme_code (str/int): The scheme code.
            as_json (bool): If True, return the data in JSON format.
            as_dataframe (bool): If True, return the data as a DataFrame.
        Returns:
            str: The historical NAV data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_scheme_historical_nav,
                str(scheme_code),
                as_json=as_json,
                as_Dataframe=as_dataframe,
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving historical NAV for {scheme_code}: {str(e)}"

    def mf_history(
        self,
        scheme_code,
        start: str = None,
        end: str = None,
        period: str = None,
        as_dataframe: bool = False,
    ):
        """
        Retrieve historical NAV data with one day change using mf.history().
        Args:
            scheme_code (str/int): The scheme code.
            start (str): Start date (optional).
            end (str): End date (optional).
            period (str): Period (e.g., '3mo').
            as_dataframe (bool): If True, return as DataFrame.
        Returns:
            str: Historical NAV data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.history,
                str(scheme_code),
                start=start,
                end=end,
                period=period,
                as_dataframe=as_dataframe,
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving historical data for {scheme_code}: {str(e)}"

    def calculate_balance_units_value(self, scheme_code, units: float):
        """
        Calculate the current market value of the given number of units for a scheme.
        Args:
            scheme_code (str/int): The scheme code.
            units (float): Number of units held.
        Returns:
            str: Market value details.
        """
        try:
            result = self._mftool_retry(
                self.mftool.calculate_balance_units_value, str(scheme_code), units
            )
            return str(result)
        except Exception as e:
            return f"Error calculating balance units value for {scheme_code}: {str(e)}"

    def calculate_returns(
        self,
        scheme_code,
        balanced_units: float,
        monthly_sip: float,
        investment_in_months: int,
    ):
        """
        Calculate the absolute and IRR annualised returns.
        Args:
            scheme_code (str/int): The scheme code.
            balanced_units (float): Units balance.
            monthly_sip (float): Monthly SIP amount.
            investment_in_months (int): Investment duration in months.
        Returns:
            str: Returns calculation details.
        """
        try:
            result = self._mftool_retry(
                self.mftool.calculate_returns,
                code=str(scheme_code),
                balanced_units=balanced_units,
                monthly_sip=monthly_sip,
                investment_in_months=investment_in_months,
            )
            return str(result)
        except Exception as e:
            return f"Error calculating returns for {scheme_code}: {str(e)}"

    def get_open_ended_equity_scheme_performance(self, as_json: bool = True):
        """
        Retrieve daily performance of open ended equity schemes.
        Args:
            as_json (bool): If True, return data in JSON format.
        Returns:
            str: Performance data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_open_ended_equity_scheme_performance, as_json
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving equity scheme performance: {str(e)}"

    def get_open_ended_debt_scheme_performance(self, as_json: bool = True):
        """
        Retrieve daily performance of open ended debt schemes.
        Args:
            as_json (bool): If True, return data in JSON format.
        Returns:
            str: Performance data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_open_ended_debt_scheme_performance, as_json
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving debt scheme performance: {str(e)}"

    def get_open_ended_hybrid_scheme_performance(self, as_json: bool = True):
        """
        Retrieve daily performance of open ended hybrid schemes.
        Args:
            as_json (bool): If True, return data in JSON format.
        Returns:
            str: Performance data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_open_ended_hybrid_scheme_performance, as_json
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving hybrid scheme performance: {str(e)}"

    def get_open_ended_solution_scheme_performance(self, as_json: bool = True):
        """
        Retrieve daily performance of open ended solution schemes.
        Args:
            as_json (bool): If True, return data in JSON format.
        Returns:
            str: Performance data.
        """
        try:
            result = self._mftool_retry(
                self.mftool.get_open_ended_solution_scheme_performance, as_json
            )
            return str(result)
        except Exception as e:
            return f"Error retrieving solution scheme performance: {str(e)}"

    def get_all_amc_profiles(self, as_json: bool = True):
        """
        Retrieve profile data of all AMCs.
        Args:
            as_json (bool): If True, return data in JSON format.
        Returns:
            str: AMC profiles.
        """
        try:
            result = self._mftool_retry(self.mftool.get_all_amc_profiles, as_json)
            return str(result)
        except Exception as e:
            return f"Error retrieving AMC profiles: {str(e)}"
