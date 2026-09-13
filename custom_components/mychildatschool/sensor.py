"""Sensors for MyChildAtSchool."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MCASCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the MCAS sensors."""
    coordinator: MCASCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AttendanceTodaySensor(coordinator, entry),
            AttendancePercentSensor(coordinator, entry),
            BehaviourEventsSensor(coordinator, entry),
            DetentionsSensor(coordinator, entry),
            DinnerBalanceSensor(coordinator, entry),
        ]
    )


class MCASEntity(CoordinatorEntity[MCASCoordinator], SensorEntity):
    """Shared device and naming."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MCASCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.unique_id))},
            name=coordinator.data.get("student_name") or "MyChildAtSchool",
            manufacturer="Bromcom",
            model="MyChildAtSchool",
            configuration_url="https://www.mychildatschool.com/MCAS/MCSParentLogin",
        )


class AttendanceTodaySensor(MCASEntity):
    """Whether the pupil was registered present today."""

    _attr_icon = "mdi:school"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "attendance_today")
        self._attr_name = "Attendance today"

    @property
    def native_value(self) -> str:
        day = self.coordinator.data.get("attendance_today")
        if day is None or not day.periods:
            # Weekends, holidays and mornings before registration all land here.
            return "No data"
        return "Present" if day.present else "Not present"

    @property
    def extra_state_attributes(self) -> dict:
        day = self.coordinator.data.get("attendance_today")
        if day is None:
            return {}
        return {
            "summary": day.summary,
            "periods": [
                {
                    "period": p.get("PeriodName"),
                    "mark": p.get("MarkMeaning"),
                    "description": p.get("MarkDescription"),
                    "subject": p.get("SubjectName"),
                }
                for p in day.periods
            ],
        }


class AttendancePercentSensor(MCASEntity):
    """Percentage of recorded school days present over the lookback window."""

    _attr_icon = "mdi:chart-line"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "attendance_percent")
        self._attr_name = "Attendance this week"

    @property
    def native_value(self):
        return self.coordinator.data.get("attendance_pct")

    @property
    def extra_state_attributes(self) -> dict:
        days = self.coordinator.data.get("attendance_days") or []
        return {
            "days_recorded": len(days),
            "days": {d.day.isoformat(): d.summary for d in days},
        }


class BehaviourEventsSensor(MCASEntity):
    """Count of behaviour events recorded in the lookback window."""

    _attr_icon = "mdi:account-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "behaviour_events")
        self._attr_name = "Behaviour events"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("behaviour_events") or [])

    @property
    def extra_state_attributes(self) -> dict:
        events = self.coordinator.data.get("behaviour_events") or []
        return {"events": events[:20]}


class DetentionsSensor(MCASEntity):
    """Outstanding detentions."""

    _attr_icon = "mdi:clock-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "detentions")
        self._attr_name = "Detentions"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("detentions") or [])

    @property
    def extra_state_attributes(self) -> dict:
        return {"detentions": self.coordinator.data.get("detentions") or []}


class DinnerBalanceSensor(MCASEntity):
    """Dinner money credit balance."""

    _attr_icon = "mdi:food"
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "dinner_balance")
        self._attr_name = "Dinner balance"

    @property
    def native_value(self):
        return self.coordinator.data.get("dinner_balance")
