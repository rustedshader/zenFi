import yfinance
from langchain_core.tools import tool
import json


async def get_stock_fastinfo(symbol: str):
    try:
        dat = yfinance.Ticker(symbol)
        return dat.fast_info
    except Exception as e:
        return f"Error getting fast info for {symbol}: {str(e)}"


@tool
def get_stock_currency(symbol: str) -> str:
    """
    Retrieves the currency for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The currency or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.currency)
    except Exception as e:
        return f"Error retrieving currency for {symbol}: {str(e)}"


@tool
def get_stock_day_high(symbol: str) -> str:
    """
    Retrieves the day's high price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The day's high price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.day_high)
    except Exception as e:
        return f"Error retrieving day high for {symbol}: {str(e)}"


@tool
def get_stock_day_low(symbol: str) -> str:
    """
    Retrieves the day's low price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The day's low price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.day_low)
    except Exception as e:
        return f"Error retrieving day low for {symbol}: {str(e)}"


@tool
def get_stock_exchange(symbol: str) -> str:
    """
    Retrieves the exchange for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The exchange or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.exchange)
    except Exception as e:
        return f"Error retrieving exchange for {symbol}: {str(e)}"


@tool
def get_stock_fifty_day_average(symbol: str) -> str:
    """
    Retrieves the fifty-day average stock price for the given symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: Formatted string with fifty-day average stock price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.fifty_day_average)
    except Exception as e:
        return f"Error retrieving fifty-day average stock price for {symbol}: {str(e)}"


@tool
def get_stock_last_price(symbol: str) -> str:
    """
    Retrieves the last stock price for the given symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: Formatted string with the last stock price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.last_price)
    except Exception as e:
        return f"Error retrieving stock price for {symbol}: {str(e)}"


@tool
def get_stock_last_volume(symbol: str) -> str:
    """
    Retrieves the last trading volume for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The last volume or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.last_volume)
    except Exception as e:
        return f"Error retrieving last volume for {symbol}: {str(e)}"


@tool
def get_stock_market_cap(symbol: str) -> str:
    """
    Retrieves the market capitalization for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The market cap or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.market_cap)
    except Exception as e:
        return f"Error retrieving market cap for {symbol}: {str(e)}"


@tool
def get_stock_open(symbol: str) -> str:
    """
    Retrieves the opening price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The opening price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.open)
    except Exception as e:
        return f"Error retrieving open price for {symbol}: {str(e)}"


@tool
def get_stock_previous_close(symbol: str) -> str:
    """
    Retrieves the previous closing price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The previous close price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.previous_close)
    except Exception as e:
        return f"Error retrieving previous close for {symbol}: {str(e)}"


@tool
def get_stock_quote_type(symbol: str) -> str:
    """
    Retrieves the quote type for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The quote type or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.quote_type)
    except Exception as e:
        return f"Error retrieving quote type for {symbol}: {str(e)}"


@tool
def get_stock_regular_market_previous_close(symbol: str) -> str:
    """
    Retrieves the regular market previous close price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The regular market previous close price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.regular_market_previous_close)
    except Exception as e:
        return f"Error retrieving regular market previous close for {symbol}: {str(e)}"


@tool
def get_stock_shares(symbol: str) -> str:
    """
    Retrieves the number of shares for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The number of shares or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.shares)
    except Exception as e:
        return f"Error retrieving shares for {symbol}: {str(e)}"


@tool
def get_stock_ten_day_average_volume(symbol: str) -> str:
    """
    Retrieves the ten-day average volume for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The ten-day average volume or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.ten_day_average_volume)
    except Exception as e:
        return f"Error retrieving ten-day average volume for {symbol}: {str(e)}"


@tool
def get_stock_three_month_average_volume(symbol: str) -> str:
    """
    Retrieves the three-month average volume for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The three-month average volume or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.three_month_average_volume)
    except Exception as e:
        return f"Error retrieving three-month average volume for {symbol}: {str(e)}"


@tool
def get_stock_timezone(symbol: str) -> str:
    """
    Retrieves the timezone for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The timezone or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.timezone)
    except Exception as e:
        return f"Error retrieving timezone for {symbol}: {str(e)}"


@tool
def get_stock_two_hundred_day_average(symbol: str) -> str:
    """
    Retrieves the two-hundred-day average stock price for the given symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: Formatted string with two-hundred-day average stock price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.two_hundred_day_average)
    except Exception as e:
        return f"Error retrieving two-hundred-day average stock price for {symbol}: {str(e)}"


@tool
def get_stock_year_change(symbol: str) -> str:
    """
    Retrieves the year change for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The year change or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.year_change)
    except Exception as e:
        return f"Error retrieving year change for {symbol}: {str(e)}"


@tool
def get_stock_year_high(symbol: str) -> str:
    """
    Retrieves the year's high price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The year's high price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.year_high)
    except Exception as e:
        return f"Error retrieving year high for {symbol}: {str(e)}"


@tool
def get_stock_year_low(symbol: str) -> str:
    """
    Retrieves the year's low price for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The year's low price or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        return str(dat.fast_info.year_low)
    except Exception as e:
        return f"Error retrieving year low for {symbol}: {str(e)}"


@tool
def get_stock_history(symbol: str) -> str:
    """
    Retrieves historical price data for the given stock symbol over the last month.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The historical data as a string or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        hist = dat.history(period="1mo", interval="1d")
        return hist.to_string()
    except Exception as e:
        return f"Error retrieving historical data for {symbol}: {str(e)}"


@tool
def get_stock_income_statement(symbol: str) -> str:
    """
    Retrieves the annual income statement for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The income statement as a string or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        stmt = dat.income_stmt
        return stmt.to_string()
    except Exception as e:
        return f"Error retrieving income statement for {symbol}: {str(e)}"


@tool
def get_stock_info(symbol: str) -> str:
    """
    Retrieves general information about the company for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The company information as a JSON string or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        info = dat.info
        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error retrieving company info for {symbol}: {str(e)}"


@tool
def get_stock_options_chain(symbol: str) -> str:
    """
    Retrieves the options chain for the given stock symbol for the nearest expiration date.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: The options chain (calls and puts) as a string or an error message.
    """
    try:
        dat = yfinance.Ticker(symbol)
        if not dat.options:
            return f"No options data available for {symbol}"
        expiration_date = dat.options[0]  # Uses the nearest expiration date
        chain = dat.option_chain(expiration_date)
        calls = chain.calls.to_string()
        puts = chain.puts.to_string()
        return f"Calls:\n{calls}\n\nPuts:\n{puts}"
    except Exception as e:
        return f"Error retrieving options chain for {symbol}: {str(e)}"


@tool
def get_stock_point_change(symbol: str) -> str:
    """
    Retrieves the stock price change in points for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: A formatted string with the point change (e.g., "+50.25 pts" or "-30.10 pts"), or an error message.
    """
    try:
        last_price_str = get_stock_last_price(symbol)
        previous_close_str = get_stock_previous_close(symbol)
        if "Error" in last_price_str or "Error" in previous_close_str:
            return f"Error retrieving point change for {symbol}: Invalid price data"
        last_price = float(last_price_str)
        previous_close = float(previous_close_str)
        point_change = last_price - previous_close
        point_change_str = (
            f"+{point_change:.2f} pts"
            if point_change >= 0
            else f"{point_change:.2f} pts"
        )
        return point_change_str
    except Exception as e:
        return f"Error calculating point change for {symbol}: {str(e)}"


@tool
def get_stock_percentage_change(symbol: str) -> str:
    """
    Retrieves the stock price change in percentage for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: A formatted string with the percentage change (e.g., "+2.34%" or "-1.45%"), or an error message.
    """
    try:
        last_price_str = get_stock_last_price(symbol)
        previous_close_str = get_stock_previous_close(symbol)
        if "Error" in last_price_str or "Error" in previous_close_str:
            return (
                f"Error retrieving percentage change for {symbol}: Invalid price data"
            )
        last_price = float(last_price_str)
        previous_close = float(previous_close_str)
        point_change = last_price - previous_close
        percentage_change = (point_change / previous_close) * 100
        percentage_change_str = (
            f"+{percentage_change:.2f}%"
            if percentage_change >= 0
            else f"{percentage_change:.2f}%"
        )
        return percentage_change_str
    except Exception as e:
        return f"Error calculating percentage change for {symbol}: {str(e)}"


@tool
def get_stock_price_change(symbol: str) -> str:
    """
    Retrieves the stock price change in points and percentage for the given stock symbol.
    Args:
        symbol (str): The stock ticker symbol (e.g., "RELIANCE.NS").
    Returns:
        str: A formatted string with the point change and percentage change, or an error message.
    """
    try:
        last_price_str = get_stock_last_price(symbol)
        previous_close_str = get_stock_previous_close(symbol)

        if "Error" in last_price_str or "Error" in previous_close_str:
            return f"Error retrieving price change for {symbol}: Invalid price data"

        last_price = float(last_price_str)
        previous_close = float(previous_close_str)

        point_change = last_price - previous_close

        percentage_change = (point_change / previous_close) * 100

        point_change_str = (
            f"+{point_change:.2f} pts"
            if point_change >= 0
            else f"{point_change:.2f} pts"
        )
        percentage_change_str = (
            f"+{percentage_change:.2f}%"
            if percentage_change >= 0
            else f"{percentage_change:.2f}%"
        )

        return f"Stock {symbol}: {point_change_str} ({percentage_change_str})"

    except Exception as e:
        return f"Error calculating price change for {symbol}: {str(e)}"


if __name__ == "__main__":
    symbol_to_test = "RELIANCE.NS"
    # print(f"Currency for {symbol_to_test}: {get_stock_currency(symbol_to_test)}")
    # print(f"Day High for {symbol_to_test}: {get_stock_day_high(symbol_to_test)}")
    # print(f"Last Price for {symbol_to_test}: {get_stock_last_price(symbol_to_test)}")
    # print(f"Market Cap for {symbol_to_test}: {get_stock_market_cap(symbol_to_test)}")
    # print(
    #     f"50 Day Average for {symbol_to_test}: {get_stock_fifty_day_average(symbol_to_test)}"
    # )
    # print(
    #     f"200 Day Average for {symbol_to_test}: {get_stock_two_hundred_day_average(symbol_to_test)}"
    # )
    print(get_stock_fastinfo(symbol_to_test))
