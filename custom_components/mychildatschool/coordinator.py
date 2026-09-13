"""Coordinator for MyChildAtSchool."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import AttendanceDay, MCASAuthError, MCASClient, MCASError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, WEEK_LOOKBACK_DAYS

_LOGGER = logging.getLogger(__name__)


class MCASCoordinator(DataUpdateCoordinator):
    """Fetch pupil data, keeping calls on the portal to a minimum.

    MCAS serves attendance and behaviour one day at a time, so a week costs a call
    per day. Past school days do not change, so they are cached for the life of the
    entry and only today and yesterday are re-fetched (yesterday because registers
    are sometimes corrected the next morning). Steady state is therefore a handful
    of calls per poll rather than one per day of the week.
    """

    def __init__(self, hass: HomeAssistant, client: MCASClient) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )
        self.client = client
        self._attendance: dict[date, AttendanceDay] = {}
        self._behaviour: dict[date, list[dict]] = {}

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except MCASAuthError as err:
            # Triggers HA's re-authentication flow rather than just erroring.
            raise ConfigEntryAuthFailed(str(err)) from err
        except MCASError as err:
            raise UpdateFailed(str(err)) from err

    def _window(self) -> list[date]:
        """School days to summarise: weekdays within the lookback window."""
        today = date.today()
        days = [today - timedelta(days=i) for i in range(WEEK_LOOKBACK_DAYS)]
        return [d for d in days if d.weekday() < 5]

    def _fetch(self) -> dict:
        client = self.client
        client.ensure_session()
        today = date.today()
        volatile = {today, today - timedelta(days=1)}

        for day in self._window():
            if day in self._attendance and day not in volatile:
                continue
            self._attendance[day] = client.attendance(day)
            self._behaviour[day] = client.behaviour(day)

        window = self._window()
        attendance = [self._attendance[d] for d in window if d in self._attendance]
        recorded = [a for a in attendance if a.periods]
        present = [a for a in recorded if a.present]
        events: list[dict] = []
        for day in window:
            events.extend(self._behaviour.get(day, []))

        return {
            "student_name": client.student_name,
            "school_name": client.school_name,
            "attendance_today": self._attendance.get(today),
            "attendance_days": recorded,
            "attendance_pct": (
                round(len(present) / len(recorded) * 100, 1) if recorded else None
            ),
            "behaviour_events": events,
            "detentions": client.detentions(),
            "dinner_balance": client.dinner_balance(),
        }
