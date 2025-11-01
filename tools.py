import os
import logging

from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from tool_function import *

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

tools = []

# Tool 1: Tavily Search
tavily_tool = None
if os.getenv("TAVILY_API_KEY"):
    tavily_tool = TavilySearch(max_results=3)
    logger.info("Tavily Search tool loaded.")
else:
    logger.warning("TAVILY_API_KEY not set. Tavily Search tool will not be available.")


@tool
def get_current_time_tool(timezone: str = 'UTC') -> str:
    """
    Returns the current date and time in a specified timezone. 
    Use this tool for any question about 'what time is it' or 'what is the date'.

    Args:
        timezone: The IANA timezone string (e.g., 'America/New_York', 'Europe/London', 'Asia/Kolkata').
                  Defaults to 'UTC'.
    Returns:
        A formatted string with the current date and time.
    """
    # Simply call the original function logic
    return get_current_time(timezone)

# Collect all tools
tools = [get_current_time_tool]


if tavily_tool:
    tools.append(tavily_tool)

if not tools:
    logger.error("No tools were successfully loaded! The agent will not have web search capabilities.")

