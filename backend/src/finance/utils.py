import calendar
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional
from typing import Tuple
from typing import Union

from fastapi import HTTPException
from fastapi import status

from .schemas import SubscriptionFrequency
from .schemas import TransactionType


def add_months(moment: datetime, months: int) -> datetime:
    """Adds a number of calendar months keeping the day of the month when possible."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def calculate_next_payment_date(frequency: SubscriptionFrequency, from_date: datetime) -> datetime:
    """Returns the next payment date for a recurring transaction."""
    if frequency == SubscriptionFrequency.DAILY:
        return from_date + timedelta(days=1)
    if frequency == SubscriptionFrequency.WEEKLY:
        return from_date + timedelta(weeks=1)
    if frequency == SubscriptionFrequency.MONTHLY:
        return add_months(from_date, 1)
    if frequency == SubscriptionFrequency.QUARTERLY:
        return add_months(from_date, 3)
    if frequency == SubscriptionFrequency.YEARLY:
        return add_months(from_date, 12)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported subscription frequency",
    )


def convert_amount(amount: float, source_rate: float, target_rate: float) -> float:
    """Converts an amount between two currencies using their rates to the base currency."""
    if source_rate <= 0 or target_rate <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid exchange rate")
    return round(amount * source_rate / target_rate, 2)


def balance_delta(transaction_type: TransactionType, amount: float, rate: float = 1.0) -> float:
    """Signed effect of a transaction on the account balance."""
    converted = round(amount * rate, 2)
    if transaction_type == TransactionType.INCOME:
        return converted
    return -converted


def to_datetime(value: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """Coerces ISO-8601 strings to datetime objects, keeps None untouched."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime value: {value}",
        )


def normalize_period(
    start_date: Optional[Union[datetime, str]], end_date: Optional[Union[datetime, str]]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Validates and normalizes a date range.

    A date-only end (midnight) includes the whole day: records carry daytime
    timestamps, so the boundary expands to 23:59:59.999999. Explicit end times
    (e.g. "now") are kept as-is.
    """
    start_date = to_datetime(start_date)
    end_date = to_datetime(end_date)
    if end_date is not None and end_date.time() == time(0, 0):
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be less than or equal to end_date",
        )
    return start_date, end_date
