import yfinance as yf

# Create a ticker object (using RELIANCE.NS as an example)
dat = yf.Ticker("RELIANCE.NS")

# Get and print current stock price/info
info = dat.info
print("Company Name:", info["longName"])
print("Current Price:", info["currentPrice"])
print("Previous Close:", info["previousClose"])
print("Market Cap:", info["marketCap"])

# Get and print historical data (last 5 days as an example)
hist = dat.history(period="5d")
print("\nHistorical Data (last 5 days):")
print(hist)

# Get and print specific historical data for a date range
hist_range = dat.history(start="2025-01-01", end="2025-03-24")
print("\nHistorical Data (custom range):")
print(hist_range)
