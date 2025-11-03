import datetime
import pytz
import re

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
        # Sanitize timezone input to prevent injection
        if not re.match(r'^[A-Za-z_/]+$', timezone):
            return "Error: Invalid timezone format. Please use a valid IANA timezone string."
        
        tz = pytz.timezone(timezone)
        current_time = datetime.datetime.now(tz)
        # Use safe string formatting
        safe_timezone = re.sub(r'[^A-Za-z_/]', '', timezone)
        return f"The current date and time in {safe_timezone} is: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except pytz.exceptions.UnknownTimeZoneError:
        return "Error: Unknown timezone. Please use a valid IANA timezone string (e.g., 'America/Los_Angeles')."
    except Exception:
        return "Error: Unable to get current time." 
