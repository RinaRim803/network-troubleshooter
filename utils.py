import datetime


def separator():
    """Return a visual separator line."""
    return "-" * 40


def timestamp():
    """Return the current datetime as a formatted string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
