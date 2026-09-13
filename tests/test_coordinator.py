"""Tests for the pieces of coordinator logic that are easy to get wrong."""

import pytest

from custom_components.mychildatschool.api import AttendanceDay
from custom_components.mychildatschool.coordinator import _period_order


@pytest.mark.parametrize(
    ("periods", "expected"),
    [
        (["2", "Tutor", "10", "1"], ["Tutor", "1", "2", "10"]),
        (["10", "9"], ["9", "10"]),
        (["1", "Registration", "Tutor"], ["Tutor", "1", "Registration"]),
    ],
)
def test_period_order(periods, expected):
    """Tutor is morning registration, and period 10 comes after period 2.

    Sorting the labels as plain strings gets both of these wrong.
    """
    assert sorted(periods, key=_period_order) == expected


def test_attendance_day_present_requires_every_period():
    day = AttendanceDay(
        day=None,
        periods=[{"MarkSign": "P"}, {"MarkSign": "L"}],
    )
    assert day.present is True

    partial = AttendanceDay(day=None, periods=[{"MarkSign": "P"}, {"MarkSign": "N"}])
    assert partial.present is False


def test_attendance_day_with_no_marks_is_unknown_not_absent():
    """Weekends, holidays and pre-registration mornings must not read as absent."""
    assert AttendanceDay(day=None, periods=[]).present is None
    assert AttendanceDay(day=None, periods=[]).summary == "No data"


def test_attendance_summary_lists_each_period():
    day = AttendanceDay(
        day=None,
        periods=[
            {"PeriodName": "AM", "MarkMeaning": "Present"},
            {"PeriodName": "PM", "MarkMeaning": "Late"},
        ],
    )
    assert day.summary == "AM: Present, PM: Late"
