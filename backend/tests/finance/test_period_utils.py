"""Period normalization: a date-only end boundary includes the whole day."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from src.finance.utils import normalize_period


def test_day_period_end_expands_to_end_of_day():
    start, end = normalize_period(datetime(2026, 11, 12), datetime(2026, 11, 12))

    assert start == datetime(2026, 11, 12)
    assert end == datetime(2026, 11, 12, 23, 59, 59, 999999)


def test_month_period_keeps_the_last_day():
    _, end = normalize_period(datetime(2026, 11, 1), datetime(2026, 11, 30))

    assert end == datetime(2026, 11, 30, 23, 59, 59, 999999)


def test_explicit_end_time_is_kept():
    now = datetime(2026, 11, 12, 15, 30)
    _, end = normalize_period(datetime(2026, 11, 1), now)

    assert end == now


def test_iso_strings_are_accepted():
    start, end = normalize_period("2026-11-01", "2026-11-12")

    assert start == datetime(2026, 11, 1)
    assert end == datetime(2026, 11, 12, 23, 59, 59, 999999)


def test_none_bounds_pass_through():
    assert normalize_period(None, None) == (None, None)


def test_start_after_end_rejected():
    with pytest.raises(HTTPException) as caught:
        normalize_period(datetime(2026, 11, 13), datetime(2026, 11, 12))

    assert caught.value.status_code == 400
