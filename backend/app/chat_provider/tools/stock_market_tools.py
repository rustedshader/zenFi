from io import StringIO
import json
import pandas as pd
import numpy as np
from nselib.capital_market import price_volume_and_deliverable_position_data
import yfinance as yf
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA


class StockAnalysisService:
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame column names by stripping whitespace and title-casing.
        """
        df.columns = [str(col).strip().title() for col in df.columns]
        return df

    def _parse_date(self, date_str: str) -> str:
        """
        Validate and convert a date string to the expected format (DD-MM-YYYY).
        """
        try:
            # Try to parse using common formats; then reformat.
            dt = pd.to_datetime(date_str, dayfirst=True, errors="raise")
            return dt.strftime("%d-%m-%Y")
        except Exception as e:
            raise ValueError(f"Date '{date_str}' is not in a valid format. Error: {e}")

    def _normalize_close_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure that the DataFrame contains a 'Close' column by checking for variations.
        """
        df = self._normalize_dataframe(df)
        if "Close" not in df.columns:
            # Check if 'Closeprice' exists and rename it to 'Close'
            if "Closeprice" in df.columns:
                df = df.rename(columns={"Closeprice": "Close"})
            else:
                raise ValueError(
                    f"Parsed DataFrame columns: {df.columns}. Expected a 'Close' column."
                )
        return df

    def get_historical_data(
        self, symbol: str, from_date: str, to_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical price and volume data for a stock from NSE.

        Args:
            symbol (str): Stock ticker symbol (e.g., "RELIANCE").
            from_date (str): Start date in 'DD-MM-YYYY' format.
            to_date (str): End date in 'DD-MM-YYYY' format.

        Returns:
            pd.DataFrame: Historical data with OHLCV (Open, High, Low, Close, Volume).
        """
        symbol = symbol.strip().upper()  # Normalize symbol input
        # Validate and standardize date format
        from_date = self._parse_date(from_date)
        to_date = self._parse_date(to_date)

        try:
            df = price_volume_and_deliverable_position_data(symbol, from_date, to_date)
            df = self._normalize_dataframe(df)
            return df
        except Exception as e:
            raise Exception(f"Error retrieving historical data for {symbol}: {str(e)}")

    def calculate_technical_indicators(
        self, data: pd.DataFrame, indicators: list[str]
    ) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame.")

        data = self._normalize_dataframe(data)
        data = self._normalize_close_column(data)

        if "SMA" in indicators:
            data["SMA"] = data["Close"].rolling(window=20).mean()
        if "EMA" in indicators:
            data["EMA"] = data["Close"].ewm(span=20, adjust=False).mean()
        if "RSI" in indicators:
            delta = data["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            data["RSI"] = 100 - (100 / (1 + rs))
        return data

    def predict_stock_price(
        self, data: pd.DataFrame, method: str = "average", params: dict = None
    ) -> float:
        """
        Predict the next closing price using the specified method.

        Args:
            data (pd.DataFrame): Historical stock data with a 'Close' column.
            method (str): Prediction method ('average', 'linear_regression', 'arima').
            params (dict, optional): Parameters for the method.

        Returns:
            float: Predicted next closing price.
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame.")

        data = self._normalize_dataframe(data)
        if "Close" not in data.columns:
            raise ValueError("DataFrame must contain a 'Close' column.")

        params = params or {}

        if method == "average":
            N = params.get("N", 10)
            return float(data["Close"].tail(N).mean())
        elif method == "linear_regression":
            M = params.get("M", 30)
            recent_data = data.tail(M)
            X = np.arange(M).reshape(-1, 1)
            y = recent_data["Close"].values
            model = LinearRegression()
            model.fit(X, y)
            next_x = np.array([[M]])
            return float(model.predict(next_x)[0])
        elif method == "arima":
            order = params.get("order", (1, 1, 1))
            model = ARIMA(data["Close"], order=order)
            model_fit = model.fit()
            return float(model_fit.forecast(steps=1)[0])
        else:
            raise ValueError(f"Unsupported prediction method: {method}")

    def get_fundamental_data(self, symbol: str) -> dict:
        """
        Retrieve fundamental data for a stock using yfinance.

        Args:
            symbol (str): Stock ticker symbol (e.g., "RELIANCE.NS").

        Returns:
            dict: Fundamental data (e.g., P/E ratio, EPS).
        """
        symbol = symbol.strip().upper()
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "Company Name": info.get("longName", "N/A"),
                "Current Price": info.get("currentPrice", "N/A"),
                "PE Ratio": info.get("trailingPE", "N/A"),
                "EPS": info.get("trailingEps", "N/A"),
                "Dividend Yield": info.get("dividendYield", "N/A"),
            }
        except Exception as e:
            raise Exception(f"Error retrieving fundamental data for {symbol}: {str(e)}")

    def calculate_sharpe_ratio(self, data: str, risk_free_rate: float = 0.0) -> float:
        """
        Calculate the Sharpe Ratio for the stock based on daily returns.

        Args:
            data (str): JSON or CSV string representing historical stock data.
            risk_free_rate (float): Annual risk-free rate (default: 0.0).

        Returns:
            float: Sharpe Ratio.
        """
        # Try parsing as JSON
        try:
            parsed_data = json.loads(data)
            df = pd.DataFrame(parsed_data)
        except json.JSONDecodeError:
            try:
                df = pd.read_csv(StringIO(data))
            except Exception as e:
                raise ValueError(f"Failed to parse data as JSON or CSV: {e}")

        if df.empty:
            raise ValueError("Parsed DataFrame is empty.")

        # Normalize column names and ensure 'Close' column exists (fallback to 'Closeprice')
        df.columns = [str(col).strip().title() for col in df.columns]
        if "Close" not in df.columns:
            if "Closeprice" in df.columns:
                df = df.rename(columns={"Closeprice": "Close"})
            else:
                raise ValueError(
                    f"Parsed DataFrame columns: {df.columns}. Expected a 'Close' column."
                )

        # Convert the 'Close' column to numeric, coercing errors to NaN, then drop NaNs.
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Close"])
        if df.empty:
            raise ValueError("No valid numeric 'Close' values found after conversion.")

        returns = df["Close"].pct_change().dropna()
        mean_return = returns.mean() * 252  # Annualize
        std_return = returns.std() * np.sqrt(252)  # Annualize
        return (mean_return - risk_free_rate) / std_return if std_return != 0 else 0.0
