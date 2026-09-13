"""Config flow for MyChildAtSchool."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # noqa: F401

from .api import MCASAuthError, MCASClient, MCASError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})


class MCASConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ask for the parent portal login and verify it before creating the entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Collect the portal login and verify it before creating the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = await self.hass.async_add_executor_job(
                    self._verify, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except MCASAuthError:
                errors["base"] = "invalid_auth"
            except MCASError:
                errors["base"] = "cannot_connect"
            else:
                # One MCAS login covers one pupil, so the student id is the unique id.
                await self.async_set_unique_id(str(client.student_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=client.student_name or "MyChildAtSchool", data=user_input
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    @staticmethod
    def _verify(email: str, password: str) -> MCASClient:
        import requests

        session = requests.Session()
        session.headers.update({"User-Agent": "HomeAssistant-MCAS"})
        client = MCASClient(session, email, password)
        client.login()
        return client
