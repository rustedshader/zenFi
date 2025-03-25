from nselib import derivatives
from nselib import capital_market

print(capital_market.capital_market_data.equity_list())


data = derivatives.future_price_volume_data(
    symbol="SBIN", instrument="FUTSTK", from_date="20-06-2023", to_date="20-07-2023"
)

print(data)
