from datetime import datetime, timedelta
import yfinance as yf
import json
from fastapi import HTTPException


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
    result = get_charts_data(symbol)
    if result:
        print(result)
    else:
        print("No data retrieved.")
