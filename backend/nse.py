from nselib import derivatives
from nselib import capital_market
from nselib.capital_market import financial_results_for_equity

# print(capital_market.capital_market_data.equity_list())


# data = derivatives.future_price_volume_data(
#     symbol="SBIN", instrument="FUTSTK", from_date="20-06-2023", to_date="20-07-2023"
# )

# print(data)

print(
    financial_results_for_equity(
        period="1M",
        from_date="01-01-2023",
        to_date="31-12-2023",
    )["Spentex Industries Limited"]
)
