import datetime
import pytz # A library for time zones

def get_current_time(timezone: str = 'UTC') -> str:
    """
    Returns the current date and time in a specified timezone.

    Args:
        timezone: The IANA timezone string (e.g., 'America/New_York', 'Europe/London', 'Asia/Kolkata').
                  Defaults to 'UTC' if no timezone is provided.

    Returns:
        A formatted string with the current date and time.
    """
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.datetime.now(tz)
        return f"The current date and time in {timezone} is: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except pytz.exceptions.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{timezone}'. Please use a valid IANA timezone string (e.g., 'America/Los_Angeles')."
