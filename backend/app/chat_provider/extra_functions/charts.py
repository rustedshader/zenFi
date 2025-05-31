import yfinance as yf
from datetime import datetime, timedelta
import json


def get_charts_data(symbol: str):
    try:
        # Set date range
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Download stock data
        stock_data = yf.download(symbol, start=start_date, end=end_date, progress=False)

        # Check if data is valid
        if stock_data is not None and not stock_data.empty:
            # Convert to JSON with formatted output
            json_data = stock_data.head().to_json(orient="index", date_format="epoch")
            parsed_json = json.loads(json_data)
            formatted_json = json.dumps(parsed_json, indent=4)
            return formatted_json
        else:
            return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


# Example usage
if __name__ == "__main__":
    symbol = "RELIANCE.NS"
    result = get_charts_data(symbol)
    if result:
        print(result)
    else:
        print("No data retrieved.")
