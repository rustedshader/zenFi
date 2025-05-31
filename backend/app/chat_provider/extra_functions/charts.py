import yfinance
from datetime import datetime, timedelta


def get_charts_data(symbol: str):
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    stock_data = yfinance.download(symbol, start=start_date, end=end_date)
    if stock_data is not None and not stock_data.empty:
        return stock_data.head().to_json(orient="index")
    else:
        return None
