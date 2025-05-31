import requests
from dotenv import load_dotenv
import os
from forex_python.converter import CurrencyRates

load_dotenv()

FIXER_API_KEY = os.environ["FIXER_API_KEY"]


class CurrencyConverter:
    rates = {}

    def __init__(self):
        self.update_rates()

    def update_rates(self):
        url = f"http://data.fixer.io/api/latest?access_key={FIXER_API_KEY}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()

            if not data.get("success", False):
                raise ValueError(
                    f"Fixer API error: {data.get('error', 'Unknown error')}"
                )

            self.rates = data["rates"]
        except (requests.RequestException, ValueError) as e:
            raise Exception(f"Failed to fetch rates from Fixer API: {str(e)}")

    def convert(self, from_currency, to_currency, amount):
        if not self.rates:
            self.update_rates()

        try:
            if from_currency not in self.rates or to_currency not in self.rates:
                raise ValueError(
                    f"Currency {from_currency} or {to_currency} not supported"
                )

            if from_currency != "EUR":
                amount = amount / self.rates[from_currency]

            amount = round(amount * self.rates[to_currency], 2)
            return amount
        except (KeyError, ValueError) as e:
            raise ValueError(f"Conversion error: {str(e)}")


def get_exchange_rate(stock_currency, target_currency="INR"):
    """
    Attempts to get exchange rate using forex_python, falls back to Fixer API on failure.
    """
    try:
        c = CurrencyRates()
        return float(c.get_rate(stock_currency, target_currency))
    except Exception as e:
        print(f"forex_python failed: {str(e)}, falling back to Fixer API")
        try:
            converter = CurrencyConverter()
            return converter.convert(stock_currency, target_currency, 1.0)
        except Exception as fixer_error:
            raise Exception(f"Fixer API also failed: {str(fixer_error)}")
