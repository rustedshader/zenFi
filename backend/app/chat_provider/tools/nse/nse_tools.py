import requests

class NSE:
    def __init__(self):
        self.base_url = "https://www.nseindia.com/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.nseindia.com',
            'Accept': 'application/json',
        }

    def _create_session(self):
        """Create a new session with fresh cookies."""
        session = requests.Session()
        session.headers.update(self.headers)
        # Fetch fresh cookies by visiting the main website
        session.get("https://www.nseindia.com")
        return session

    def _make_request(self, url):
        """Handle API requests with retry logic for 401 errors using a new session."""
        session = self._create_session()
        response = session.get(url)
        if response.status_code == 401:
            session = self._create_session()  # Create a new session for retry
            response = session.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error fetching data: {response.status_code}")

    def market_status(self):
        market_status_url = f"{self.base_url}/marketStatus"
        return self._make_request(market_status_url)

    def stock_price_all(self):
        stock_price_url = f"{self.base_url}/equity-stockIndices?index=NIFTY%2050"
        return self._make_request(stock_price_url)

    def stock_price(self, symbol):
        stock_price_url = f"{self.base_url}/quote-equity?symbol={symbol}"
        return self._make_request(stock_price_url)

    def equity_meta_info(self, symbol):
        equity_meta_info_url = f"{self.base_url}/equity-meta-info?symbol={symbol}"
        return self._make_request(equity_meta_info_url)
    def broad_market_chart(self,symbol):
        # Example: NIFTY 50
        stock_chart_url = f"{self.base_url}/NextApi/apiClient?functionName=getGraphChart&&type={symbol}&flag=1D"
        return self._make_request(stock_chart_url)
    
    def broad_market_heatmap(self):
        broad_market_heatmap_url = f"{self.base_url}/heatmap-index?type=Broad%20Market%20Indices"
        return self._make_request(broad_market_heatmap_url)
    
    def sectoral_indices_heatmap(self):
        broad_market_heatmap_url = f"{self.base_url}/heatmap-index?type=Sectoral%20Indices"
        return self._make_request(broad_market_heatmap_url)
    
    def thematic_indices_heatmap(self):
        broad_market_heatmap_url = f"{self.base_url}/heatmap-index?type=Thematic%20Indices"
        return self._make_request(broad_market_heatmap_url)
    
    def strategy_indices_heatmap(self):
        broad_market_heatmap_url = f"{self.base_url}/heatmap-index?type=Strategy%20Indices"
        return self._make_request(broad_market_heatmap_url)

    def stock_trade_info(self, symbol):
        stock_trade_info_url = f"{self.base_url}/quote-equity?symbol={symbol}&section=trade_info"
        return self._make_request(stock_trade_info_url)

    def stock_chart_data(self, symbol):
        stock_chart_data_url = f"{self.base_url}/chart-databyindex-dynamic?index={symbol}&type=symbol"
        return self._make_request(stock_chart_data_url)

    def stock_top_corp_info(self, symbol):
        stock_top_corp_info_url = f"{self.base_url}/top-corp-info?symbol={symbol}&market=equities"
        return self._make_request(stock_top_corp_info_url)

    def stock_historical_equity_data(self, symbol):
        stock_historical_equity_data_url = f"{self.base_url}/historical/cm/equity?symbol={symbol}"
        return self._make_request(stock_historical_equity_data_url)

    def stock_equity_years(self, symbol):
        stock_equity_years_url = f"{self.base_url}/historical/cm/equity/years?symbol={symbol}"
        return self._make_request(stock_equity_years_url)

    def stock_high_low(self, symbol):
        stock_high_low_url = f"{self.base_url}/historical/cm/high-low?symbol={symbol}"
        return self._make_request(stock_high_low_url)

    def stock_high_low_all_time(self, symbol):
        stock_high_low_all_time_url = f"{self.base_url}/historical/cm/all-time-high-low?symbol={symbol}"
        return self._make_request(stock_high_low_all_time_url)

    def stock_high_low_year(self, symbol, year, month, day):
        stock_high_low_year_url = f"{self.base_url}/historical/cm/high-low?symbol={symbol}&year={year}&month={month}&day={day}"
        return self._make_request(stock_high_low_year_url)

    def stock_master_quote(self):
        stock_master_quote_url = f"{self.base_url}/master-quote"
        return self._make_request(stock_master_quote_url)

    def stock_quote_derivative(self, symbol):
        stock_quote_derivative_url = f"{self.base_url}/quote-derivative?symbol={symbol}"
        return self._make_request(stock_quote_derivative_url)

    def stock_quote_slb(self, symbol):
        stock_quote_slb_url = f"{self.base_url}/quote-slb?index={symbol}"
        return self._make_request(stock_quote_slb_url)

if __name__ == "__main__":
    nse = NSE()
    print(nse.broad_market_chart("NIFTY BANK"))