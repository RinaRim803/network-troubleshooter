import datetime


def separator() -> str:
    """Return a visual separator line."""
    return "-" * 40


def timestamp() -> str:
    """Return the current datetime as a formatted string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
