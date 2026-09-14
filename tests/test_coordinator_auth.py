"""The coordinator must tolerate a blip but still surface a real password change."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mychildatschool.api import MCASAuthError
from custom_components.mychildatschool.const import AUTH_FAILURES_BEFORE_REAUTH
from custom_components.mychildatschool.coordinator import MCASCoordinator


def _coordinator(hass):
    return MCASCoordinator(hass, MagicMock())


async def test_single_auth_failure_does_not_demand_reauth(hass):
    """One failure must be retried, not escalated.

    Escalating immediately stopped all polling and left the integration dead for
    hours after a momentary MCAS hiccup.
    """
    coordinator = _coordinator(hass)
    with (
        patch.object(coordinator, "_fetch", side_effect=MCASAuthError("Login failed")),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()
    assert coordinator._auth_failures == 1


async def test_repeated_auth_failures_do_demand_reauth(hass):
    """A genuinely changed password must still reach the re-auth prompt."""
    coordinator = _coordinator(hass)
    with patch.object(coordinator, "_fetch", side_effect=MCASAuthError("Login failed")):
        for _ in range(AUTH_FAILURES_BEFORE_REAUTH - 1):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


async def test_a_success_resets_the_failure_count(hass):
    """A recovered poll must not leave the integration one blip from re-auth."""
    coordinator = _coordinator(hass)
    with (
        patch.object(coordinator, "_fetch", side_effect=MCASAuthError("Login failed")),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()
    assert coordinator._auth_failures == 1

    with patch.object(coordinator, "_fetch", return_value={"student_name": "Alex"}):
        assert await coordinator._async_update_data() == {"student_name": "Alex"}
    assert coordinator._auth_failures == 0
