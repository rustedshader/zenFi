# schemas.py
from typing import Annotated, List, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[List, add_messages]


class ConversationState(TypedDict):
    messages: List


class PriceVolumeDeliverableInput(BaseModel):
    symbol: str = Field(..., description="The stock symbol, e.g., 'RELIANCE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")


class IndexDataInput(BaseModel):
    index: str = Field(..., description="The NSE index, e.g., 'NIFTY 50'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


class FinancialResultsInput(BaseModel):
    symbol: str = Field(..., description="The stock symbol, e.g., 'RELIANCE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")
    fo_sec: bool = Field(None, description="F&O security flag, optional")
    fin_period: str = Field(
        "Quarterly", description="Financial period, e.g., 'Quarterly', optional"
    )


class FuturePriceVolumeInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'BANKNIFTY'")
    instrument: str = Field(..., description="Instrument type, 'FUTIDX' or 'FUTSTK'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


class OptionPriceVolumeInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'NIFTY'")
    instrument: str = Field(..., description="Instrument type, 'OPTIDX' or 'OPTSTK'")
    option_type: str = Field(..., description="Option type, 'PE' or 'CE'")
    from_date: str = Field(
        None, description="Start date in 'dd-mm-yyyy' format, optional"
    )
    to_date: str = Field(None, description="End date in 'dd-mm-yyyy' format, optional")
    period: str = Field(None, description="Time period, e.g., '1M', optional")


class LiveOptionChainInput(BaseModel):
    symbol: str = Field(..., description="The stock or index symbol, e.g., 'BANKNIFTY'")
    expiry_date: str = Field(
        None, description="Expiry date in 'dd-mm-yyyy' format, optional"
    )
    oi_mode: str = Field(
        "full", description="Open interest mode, 'full' or 'compact', optional"
    )


class HistoricalDataInput(BaseModel):
    symbol: str = Field(..., description="The NSE stock symbol, e.g., 'RELIANCE'")
    from_date: str = Field(..., description="Start date in 'dd-mm-yyyy' format")
    to_date: str = Field(..., description="End date in 'dd-mm-yyyy' format")


class WebResearchInput(BaseModel):
    symbol: str


class MFAvailableSchemesInput(BaseModel):
    amc: str = Field(..., description="AMC name, e.g., 'ICICI'")


class WebScrapeInput(BaseModel):
    url: str = Field(..., description="URL to scrape data from")


class MFQuoteInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code, e.g., '119597'")
    as_json: bool = Field(False, description="Return data in JSON format if true.")


class MFDetailsInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code, e.g., '117865'")
    as_json: bool = Field(False, description="Return data in JSON format if true.")


class MFHistoricalNAVInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code, e.g., '119597'")
    as_json: bool = Field(False, description="Return data in JSON format if true.")
    as_dataframe: bool = Field(False, description="Return data as a DataFrame if true.")


class MFHistoryInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code")
    start: str = Field(None, description="Start date in 'dd-mm-yyyy' format (optional)")
    end: str = Field(None, description="End date in 'dd-mm-yyyy' format (optional)")
    period: str = Field(None, description="Period (e.g., '3mo', optional)")
    as_dataframe: bool = Field(False, description="Return as a DataFrame if true.")


class MFBalanceUnitsValueInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code, e.g., '119597'")
    units: float = Field(..., description="Number of units held.")


class MFReturnsInput(BaseModel):
    scheme_code: str = Field(..., description="Mutual fund scheme code, e.g., '119062'")
    balanced_units: float = Field(..., description="Units balance")
    monthly_sip: float = Field(..., description="Monthly SIP amount")
    investment_in_months: int = Field(..., description="Investment duration in months")


class MFPerformanceInput(BaseModel):
    as_json: bool = Field(True, description="Return data in JSON format if true.")


class MFAllAMCProfilesInput(BaseModel):
    as_json: bool = Field(True, description="Return data in JSON format if true.")


class NoInput(BaseModel):
    pass
