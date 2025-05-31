import datetime
import pytz
from langchain.tools import tool


@tool
def get_current_datetime() -> str:
    """
    Returns the current date and time in India (IST) in ISO 8601 format.

    Returns:
        str: Current date and time in India in the format 'YYYY-MM-DD HH:MM:SS'
    """
    india_tz = pytz.timezone("Asia/Kolkata")
    return datetime.datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S")
