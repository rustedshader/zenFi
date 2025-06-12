from datetime import datetime, timedelta
import yfinance as yf
import json
from fastapi import HTTPException
import requests
import time


def get_stock_info(symbol: str) -> str:
    """
    Retrieves general information about the company for the given stock symbol.
    Uses multiple fallback methods to handle API rate limiting and authentication issues.

    Args:
        symbol (str): The stock ticker symbol (e.g., "NVDA", "RELIANCE.NS").
    Returns:
        str: The company information as a JSON string or an error message.
    """

    # Method 1: Try with custom headers and session
    def method_1_with_headers():
        try:
            # Create a session with proper headers
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            ticker = yf.Ticker(symbol, session=session)
            info = ticker.info

            if info and len(info) > 1:  # Basic validation
                return json.dumps(info, indent=2, default=str)
            else:
                return None

        except Exception as e:
            print(f"Method 1 failed: {str(e)}")
            return None

    # Method 2: Try with retry mechanism
    def method_2_with_retry():
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    if info and len(info) > 1:
                        return json.dumps(info, indent=2, default=str)

                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff

                except Exception as retry_error:
                    if attempt == max_retries - 1:
                        raise retry_error
                    time.sleep(2**attempt)

        except Exception as e:
            print(f"Method 2 failed: {str(e)}")
            return None

    # Method 3: Alternative data extraction
    def method_3_alternative_data():
        try:
            ticker = yf.Ticker(symbol)

            # Try to get basic info using different methods
            basic_info = {}

            # Get historical data to verify ticker exists
            hist = ticker.history(period="5d")
            if hist.empty:
                return None

            # Get current price
            current_data = ticker.history(period="1d")
            if not current_data.empty:
                basic_info["currentPrice"] = float(current_data["Close"].iloc[-1])
                basic_info["previousClose"] = float(current_data["Close"].iloc[-1])

            # Try to get some basic info
            try:
                info = ticker.info
                if info:
                    # Extract key fields that usually work
                    key_fields = [
                        "symbol",
                        "shortName",
                        "longName",
                        "sector",
                        "industry",
                        "marketCap",
                        "enterpriseValue",
                        "trailingPE",
                        "forwardPE",
                        "dividendYield",
                        "beta",
                        "fiftyTwoWeekLow",
                        "fiftyTwoWeekHigh",
                    ]

                    for field in key_fields:
                        if field in info and info[field] is not None:
                            basic_info[field] = info[field]
            except:
                pass

            # Get financials if possible
            try:
                financials = ticker.financials
                if not financials.empty:
                    basic_info["hasFinancials"] = True
            except:
                basic_info["hasFinancials"] = False

            if basic_info:
                basic_info["symbol"] = symbol
                basic_info["dataSource"] = "yfinance_alternative"
                return json.dumps(basic_info, indent=2, default=str)
            else:
                return None

        except Exception as e:
            print(f"Method 3 failed: {str(e)}")
            return None

    # Method 4: Minimal info extraction
    def method_4_minimal():
        try:
            ticker = yf.Ticker(symbol)

            # Just try to get current price and basic validation
            hist = ticker.history(period="1d")
            if not hist.empty:
                minimal_info = {
                    "symbol": symbol,
                    "currentPrice": float(hist["Close"].iloc[-1]),
                    "volume": int(hist["Volume"].iloc[-1]),
                    "high": float(hist["High"].iloc[-1]),
                    "low": float(hist["Low"].iloc[-1]),
                    "open": float(hist["Open"].iloc[-1]),
                    "dataSource": "yfinance_minimal",
                }
                return json.dumps(minimal_info, indent=2, default=str)
            else:
                return None

        except Exception as e:
            print(f"Method 4 failed: {str(e)}")
            return None

    # Try methods in order
    methods = [
        ("Enhanced Headers", method_1_with_headers),
        ("Retry Mechanism", method_2_with_retry),
        ("Alternative Data", method_3_alternative_data),
        ("Minimal Info", method_4_minimal),
    ]

    for method_name, method_func in methods:
        print(f"Trying {method_name} for {symbol}")
        result = method_func()
        if result:
            print(f"Success with {method_name}")
            return result
        time.sleep(1)  # Brief pause between methods

    # If all methods fail
    return f"Error: Unable to retrieve company info for {symbol}. All methods failed - possible API rate limiting or symbol not found."


def get_charts_data(symbol: str):
    try:
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Fetch daily stock data
        stock_data = yf.download(symbol, start=start_date, end=end_date, interval="1d")

        if stock_data is None or stock_data.empty:
            raise HTTPException(
                status_code=404, detail=f"No data found for symbol {symbol}"
            )

        # Convert to JSON with epoch timestamps
        json_data = stock_data.to_json(orient="index", date_format="epoch")
        parsed_json = json.loads(json_data)
        formatted_json = json.dumps(parsed_json, indent=4)
        return formatted_json

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching data for {symbol}: {str(e)}"
        )


if __name__ == "__main__":
    symbol = "RELIANCE.NS"
    result = get_stock_info(symbol)
    if result:
        print(result)
    else:
        print("No data retrieved.")
    # result = get_charts_data(symbol)
    # if result:
    #     print(result)
    # else:
    #     print("No data retrieved.")
