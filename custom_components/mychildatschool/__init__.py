"""The MyChildAtSchool (MCAS) integration."""
from __future__ import annotations

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import MCASClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import MCASCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyChildAtSchool from a config entry."""
    session = await hass.async_add_executor_job(requests.Session)
    session.headers.update({"User-Agent": "HomeAssistant-MCAS"})
    client = MCASClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = MCASCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
