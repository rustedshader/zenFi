import requests
from dotenv import load_dotenv
import os

load_dotenv()

FIXER_API_KEY = os.environ["FIXER_API_KEY"]
EXCHANGERATE_API_KEY = os.environ["EXCHANGERATE_API_KEY"]


class CurrencyConverter:
    rates = {}

    def __init__(self):
        self.update_rates()

    def update_rates(self):
        # Try Fixer API first
        url_fixer = f"http://data.fixer.io/api/latest?access_key={FIXER_API_KEY}"
        try:
            response = requests.get(url_fixer, timeout=5)
            response.raise_for_status()
            data = response.json()

            if not data.get("success", False):
                raise ValueError(
                    f"Fixer API error: {data.get('error', 'Unknown error')}"
                )

            self.rates = data["rates"]
            return
        except (requests.RequestException, ValueError) as e:
            print(f"Fixer API failed: {str(e)}, falling back to ExchangeRate-API")

        # Fallback to ExchangeRate-API with EUR as base
        url_exchangerate = (
            f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/latest/INR"
        )
        try:
            response = requests.get(url_exchangerate, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                raise ValueError(
                    f"ExchangeRate-API error: {data.get('error-type', 'Unknown error')}"
                )

            self.rates = data["conversion_rates"]
        except (requests.RequestException, ValueError) as e:
            raise Exception(f"ExchangeRate-API also failed: {str(e)}")

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
    Gets exchange rate using Fixer API with ExchangeRate-API as backup.
    """
    try:
        converter = CurrencyConverter()
        return converter.convert(stock_currency, target_currency, 1.0)
    except Exception as error:
        raise Exception(f"Currency conversion failed: {str(error)}")
