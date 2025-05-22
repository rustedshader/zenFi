import time
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import WikipediaLoader
from langchain_community.utilities import SearxSearchWrapper
from langchain_community.tools import BraveSearch
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.tools import YouTubeSearchTool
from nselib.capital_market import (
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
import requests
import yfinance as yf
from langchain_community.document_loaders import YoutubeLoader
import pandas as pd
import logging
import datetime as dt
from io import BytesIO, StringIO
from nselib.libutil import (
    validate_date_param,
    derive_from_and_to_date,
    cleaning_nse_symbol,
    nse_urlfetch,
    cleaning_column_name,
)
from nselib.constants import (
    price_volume_and_deliverable_position_data_columns,
    dd_mm_yyyy,
    index_data_columns,
)
import xml.etree.ElementTree as ET

from mftool import Mftool

logging.basicConfig(level=logging.INFO)


class NSEDataNotFound(Exception):
    pass


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
        print(f"Visiting URL: {query}")
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
        print(f"Visiting URL: {url}")
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

    # -------- New NSE data methods --------

    def get_price_volume_and_deliverable_position_data(
        self, symbol: str, from_date: str, to_date: str
    ):
        """
        Fetch price, volume, and deliverable data for a symbol between two dates.

        Args:
            symbol (str): Stock symbol (e.g., "SBIN").
            from_date (str): Start date in "dd-mm-YYYY" format.
            to_date (str): End date in "dd-mm-YYYY" format.

        Returns:
            pd.DataFrame: DataFrame with the fetched data.

        Raises:
            NSEDataNotFound: If data cannot be fetched from NSE.
        """
        origin_url = "https://www.nseindia.com/report-detail/eq_security"
        url = "https://www.nseindia.com/api/historical/securityArchives?"
        payload = f"from={from_date}&to={to_date}&symbol={symbol}&dataType=priceVolumeDeliverable&series=ALL&csv=true"

        response = nse_urlfetch(url + payload, origin_url=origin_url)
        if response.status_code != 200:
            raise NSEDataNotFound(
                f"Failed to fetch data for {symbol} from {from_date} to {to_date}: Status {response.status_code}"
            )

        data_text = response.text.replace("\x82", "").replace("â¹", "In Rs")
        data_df = pd.read_csv(StringIO(data_text))
        data_df.columns = [name.replace(" ", "") for name in data_df.columns]
        return data_df

    def get_price_volume_and_deliverable_data(
        self,
        symbol: str,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
    ):
        """
        Retrieve historical price, volume, and deliverable data for a stock.

        Args:
            symbol (str): Stock symbol (e.g., "SBIN").
            from_date (str, optional): Start date in "dd-mm-YYYY" format.
            to_date (str, optional): End date in "dd-mm-YYYY" format.
            period (str, optional): Period like "1D", "1W", "1M", "6M", "1Y".

        Returns:
            pd.DataFrame: DataFrame containing the data.

        Raises:
            ValueError: If date parameters are invalid.
            NSEDataNotFound: If data fetch fails.

        Example:
            nse.get_price_volume_and_deliverable_data(symbol="SBIN", period="1M")
        """
        try:
            logging.info(f"Fetching price/volume/deliverable data for {symbol}")
            validate_date_param(from_date, to_date, period)
            symbol = cleaning_nse_symbol(symbol)
            from_date, to_date = derive_from_and_to_date(from_date, to_date, period)

            from_date_dt = dt.datetime.strptime(from_date, dd_mm_yyyy)
            to_date_dt = dt.datetime.strptime(to_date, dd_mm_yyyy)
            nse_df = pd.DataFrame(
                columns=price_volume_and_deliverable_position_data_columns
            )

            load_days = (to_date_dt - from_date_dt).days
            while load_days > 0:
                end_date_dt = from_date_dt + dt.timedelta(days=min(364, load_days))
                start_date = from_date_dt.strftime(dd_mm_yyyy)
                end_date = end_date_dt.strftime(dd_mm_yyyy)

                data_df = self.get_price_volume_and_deliverable_position_data(
                    symbol, start_date, end_date
                )
                if not data_df.empty:
                    nse_df = pd.concat([nse_df, data_df], ignore_index=True)

                from_date_dt = end_date_dt + dt.timedelta(days=1)
                load_days = (to_date_dt - from_date_dt).days

            # Clean numeric columns
            for col in [
                "TotalTradedQuantity",
                "TurnoverInRs",
                "No.ofTrades",
                "DeliverableQty",
            ]:
                if col in nse_df.columns:
                    nse_df[col] = pd.to_numeric(
                        nse_df[col].str.replace(",", ""), errors="coerce"
                    )

            return nse_df.to_json()

        except Exception as e:
            logging.error(f"Error in get_price_volume_and_deliverable_data: {str(e)}")
            raise

    def get_index_data(
        self, index: str, from_date: str = None, to_date: str = None, period: str = None
    ):
        """
        Retrieve historical data for an NSE index.

        Args:
            index (str): Index name (e.g., "NIFTY 50").
            from_date (str, optional): Start date in "dd-mm-YYYY" format.
            to_date (str, optional): End date in "dd-mm-YYYY" format.
            period (str, optional): Period like "1D", "1W", "1M", "6M", "1Y".

        Returns:
            pd.DataFrame: DataFrame with index data.

        Raises:
            ValueError: If date parameters are invalid.
            NSEDataNotFound: If data fetch fails.

        Example:
            nse.get_index_data(index="NIFTY 50", period="6M")
        """
        try:
            logging.info(f"Fetching index data for {index}")
            validate_date_param(from_date, to_date, period)
            from_date, to_date = derive_from_and_to_date(from_date, to_date, period)

            from_date_dt = dt.datetime.strptime(from_date, dd_mm_yyyy)
            to_date_dt = dt.datetime.strptime(to_date, dd_mm_yyyy)
            nse_df = pd.DataFrame(columns=index_data_columns)

            load_days = (to_date_dt - from_date_dt).days
            while load_days > 0:
                end_date_dt = from_date_dt + dt.timedelta(days=min(364, load_days))
                start_date = from_date_dt.strftime(dd_mm_yyyy)
                end_date = end_date_dt.strftime(dd_mm_yyyy)

                index_encoded = index.replace(" ", "%20").upper()
                origin_url = (
                    "https://www.nseindia.com/reports-indices-historical-index-data"
                )
                url = f"https://www.nseindia.com/api/historical/indicesHistory?indexType={index_encoded}&from={start_date}&to={end_date}"
                response = nse_urlfetch(url, origin_url=origin_url)

                if response.status_code != 200:
                    raise NSEDataNotFound(
                        f"Failed to fetch index data for {index}: Status {response.status_code}"
                    )

                data_json = response.json()
                close_df = pd.DataFrame(
                    data_json["data"]["indexCloseOnlineRecords"]
                ).drop(columns=["_id", "EOD_TIMESTAMP"])
                turnover_df = pd.DataFrame(
                    data_json["data"]["indexTurnoverRecords"]
                ).drop(columns=["_id", "HIT_INDEX_NAME_UPPER"])
                data_df = pd.merge(close_df, turnover_df, on="TIMESTAMP", how="inner")
                data_df.drop(columns="TIMESTAMP", inplace=True)
                data_df.columns = cleaning_column_name(data_df.columns)

                if not data_df.empty:
                    nse_df = pd.concat([nse_df, data_df], ignore_index=True)

                from_date_dt = end_date_dt + dt.timedelta(days=1)
                load_days = (to_date_dt - from_date_dt).days

            return nse_df.to_json()

        except Exception as e:
            logging.error(f"Error in get_index_data: {str(e)}")
            raise

    def get_bhav_copy_with_delivery(self, trade_date: str):
        """
        Retrieve bhav copy with delivery data for a specific trade date.

        Args:
            trade_date (str): Date in "dd-mm-YYYY" format (e.g., "15-08-2023").

        Returns:
            pd.DataFrame: DataFrame with bhav copy data.

        Raises:
            ValueError: If trade_date format is invalid.
            NSEDataNotFound: If data is not available.

        Example:
            nse.get_bhav_copy_with_delivery(trade_date="15-08-2023")
        """
        try:
            logging.info(f"Fetching bhav copy for {trade_date}")
            trade_date_dt = dt.datetime.strptime(trade_date, dd_mm_yyyy)
            use_date = trade_date_dt.strftime("%d%m%Y")
            url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{use_date}.csv"

            response = nse_urlfetch(url)
            if response.status_code != 200:
                raise NSEDataNotFound(
                    f"No bhav copy data available for {trade_date}: Status {response.status_code}"
                )

            bhav_df = pd.read_csv(BytesIO(response.content))
            bhav_df.columns = [name.replace(" ", "") for name in bhav_df.columns]
            bhav_df["SERIES"] = bhav_df["SERIES"].str.replace(" ", "")
            bhav_df["DATE1"] = bhav_df["DATE1"].str.replace(" ", "")
            return bhav_df.to_json()

        except ValueError as e:
            logging.error(f"Invalid date format: {str(e)}")
            raise ValueError(f"trade_date must be in 'dd-mm-YYYY' format: {str(e)}")
        except Exception as e:
            logging.error(f"Error in get_bhav_copy_with_delivery: {str(e)}")
            raise

    def get_financial_results_for_equity(
        self,
        symbol: str = None,
        from_date: str = None,
        to_date: str = None,
        period: str = None,
        fo_sec: bool = None,
        fin_period: str = "Quarterly",
    ) -> str:
        """
        Retrieve financial results for equities, optionally filtered by symbol.

        Args:
            symbol (str, optional): Stock symbol (e.g., "RELIANCE"). If None, fetches for all equities.
            from_date (str, optional): Start date in "dd-mm-YYYY" format.
            to_date (str, optional): End date in "dd-mm-YYYY" format.
            period (str, optional): Period like "1D", "1W", "1M", "6M", "1Y".
            fo_sec (bool, optional): Filter for F&O securities if True.
            fin_period (str): Financial period ("Quarterly", "Half-Yearly", "Annual", "Others").

        Returns:
            str: JSON string of financial results DataFrame.

        Raises:
            ValueError: If parameters are invalid.
            NSEDataNotFound: If data fetch fails.

        Example:
            nse.get_financial_results_for_equity(symbol="RELIANCE", period="1M", fo_sec=True, fin_period="Quarterly")
        """
        try:
            logging.info(
                f"Fetching financial results for symbol: {symbol or 'all'}, period: {fin_period}"
            )
            validate_date_param(from_date, to_date, period)
            from_date, to_date = derive_from_and_to_date(from_date, to_date, period)

            origin_url = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"
            url = "https://www.nseindia.com/api/corporates-financial-results?index=equities&"
            payload = f"from_date={from_date}&to_date={to_date}&period={fin_period}" + (
                "&fo_sec=true" if fo_sec else ""
            )

            response = nse_urlfetch(url + payload, origin_url=origin_url)
            if response.status_code != 200:
                raise NSEDataNotFound(
                    f"Failed to fetch financial data: Status {response.status_code}"
                )

            data_list = response.json()
            master_df = pd.DataFrame(data_list)
            master_df.columns = [name.replace(" ", "") for name in master_df.columns]

            # Filter by symbol if provided
            if symbol:
                master_df = master_df[master_df["symbol"].str.upper() == symbol.upper()]
                if master_df.empty:
                    logging.warning(f"No financial data found for symbol: {symbol}")
                    return pd.DataFrame().to_json()  # Return empty DataFrame as JSON

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/58.0.3029.110",
                "Accept": "*/*",
                "Referer": "https://www.nseindia.com/",
            }
            ns = {
                "in-bse-fin": "http://www.bseindia.com/xbrl/fin/2020-03-31/in-bse-fin"
            }
            keys = [
                "Symbol",
                "RevenueFromOperations",
                "ProfitBeforeTax",
                "ProfitLossForPeriod",
            ]  # Simplified for example

            fin_df = pd.DataFrame()
            for row in master_df.itertuples(index=False):
                logging.debug(f"Processing financial data for {row.symbol}")
                try:
                    resp = requests.get(row.xbrl, headers=headers, timeout=10)
                    resp.raise_for_status()
                    root = ET.fromstring(resp.content)
                    data = {
                        key: root.find(f".//in-bse-fin:{key}", ns).text
                        if root.find(f".//in-bse-fin:{key}", ns) is not None
                        else None
                        for key in keys
                    }
                    df = pd.DataFrame([data])
                    fin_df = pd.concat([fin_df, df], ignore_index=True)
                except Exception as e:
                    logging.warning(
                        f"Failed to parse financial data for {row.symbol}: {str(e)}"
                    )

            return fin_df.to_json()

        except Exception as e:
            logging.error(f"Error in get_financial_results_for_equity: {str(e)}")
            raise

    def get_fno_equity_list(self):
        """Retrieve the list of derivative equities with lot sizes."""
        try:
            df = fno_equity_list()
            return df.to_json()
        except Exception as e:
            return f"Error retrieving F&O equity list: {str(e)}"

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
            return df.to_json()
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
            return df.to_json()
        except Exception as e:
            return f"Error retrieving option price volume data: {str(e)}"

    def get_fno_bhav_copy(self, trade_date: str):
        """Retrieve F&O bhav copy for a specific trade date."""
        try:
            df = fno_bhav_copy(trade_date)
            return df.to_json()
        except Exception as e:
            return f"Error retrieving F&O bhav copy: {str(e)}"

    def get_participant_wise_open_interest(self, trade_date: str):
        """Retrieve participant-wise open interest data for a specific trade date."""
        try:
            df = participant_wise_open_interest(trade_date)
            return df.to_json()
        except Exception as e:
            return f"Error retrieving participant-wise open interest: {str(e)}"

    def get_participant_wise_trading_volume(self, trade_date: str):
        """Retrieve participant-wise trading volume data for a specific trade date."""
        try:
            df = participant_wise_trading_volume(trade_date)
            return df.to_json()
        except Exception as e:
            return f"Error retrieving participant-wise trading volume: {str(e)}"

    def get_fii_derivatives_statistics(self, trade_date: str):
        """Retrieve FII derivatives statistics for a specific trade date."""
        try:
            df = fii_derivatives_statistics(trade_date)
            return df.to_json()
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
            return df.to_json()
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

    def simulate_portfolio_growth(
        self,
        initial_investment: float,
        monthly_sip: float,
        annual_return: float,
        years: int,
    ):
        """
        Simulate portfolio growth using compound interest for an initial lump sum and monthly SIP contributions.
        """
        r = annual_return / 100
        n = years
        fv_lumpsum = initial_investment * ((1 + r) ** n)
        fv_sip = monthly_sip * (((1 + r / 12) ** (12 * n) - 1) / (r / 12))
        total = fv_lumpsum + fv_sip
        return (
            f"After {years} years, your portfolio could grow to approximately {total:.2f} "
            f"with an annual return of {annual_return}%."
        )

    def get_portfolio_summary(self, portfolio: dict):
        """
        Summarize the user's portfolio.
        Args:
            portfolio (dict): A dictionary where keys are asset names and values are amounts.
        Returns:
            str: A summary of the portfolio.
        """
        total_value = sum(portfolio.values())
        summary_lines = [f"{asset}: {value}" for asset, value in portfolio.items()]
        summary_lines.append(f"Total Portfolio Value: {total_value}")
        return "\n".join(summary_lines)
