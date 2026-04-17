"""Date range helpers — used by MetricService and SummaryService."""

from datetime import date, timedelta


def week_bounds(as_of: date) -> tuple[date, date]:
    """Return (Monday, Sunday) of the week containing as_of."""
    start = as_of - timedelta(days=as_of.weekday())
    return start, start + timedelta(days=6)


def month_bounds(as_of: date) -> tuple[date, date]:
    """Return (first, last) day of the month containing as_of."""
    first = as_of.replace(day=1)
    if as_of.month == 12:
        last = as_of.replace(day=31)
    else:
        last = as_of.replace(month=as_of.month + 1, day=1) - timedelta(days=1)
    return first, last


def quarter_bounds(as_of: date) -> tuple[date, date]:
    """Return (first, last) day of the calendar quarter containing as_of."""
    quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
    first = as_of.replace(month=quarter_start_month, day=1)
    end_month = quarter_start_month + 2
    if end_month == 12:
        last = as_of.replace(month=12, day=31)
    else:
        last = as_of.replace(month=end_month + 1, day=1) - timedelta(days=1)
    return first, last
