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
            BehaviourPointsSensor(coordinator, entry),
            DetentionsSensor(coordinator, entry),
            DinnerBalanceSensor(coordinator, entry),
            SchoolDaySensor(coordinator, entry),
            LessonsTodaySensor(coordinator, entry),
            NextLessonSensor(coordinator, entry),
            ReportsSensor(coordinator, entry),
            ClubsAndTripsSensor(coordinator, entry),
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


class BehaviourPointsSensor(MCASEntity):
    """Behaviour points for the academic year."""

    _attr_icon = "mdi:star-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "points"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "behaviour_points")
        self._attr_name = "Behaviour points"

    @property
    def native_value(self):
        return (self.coordinator.data.get("behaviour_points") or {}).get("total")

    @property
    def extra_state_attributes(self) -> dict:
        points = dict(self.coordinator.data.get("behaviour_points") or {})
        events = self.coordinator.data.get("behaviour_year_events") or []
        by_subject: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for event in events:
            subject = event.get("subject") or "Unknown"
            by_subject[subject] = by_subject.get(subject, 0) + (event.get("points") or 0)
            kind = event.get("type") or "Unknown"
            by_type[kind] = by_type.get(kind, 0) + 1
        points.update(
            {
                "academic_year": self.coordinator.data.get("behaviour_year_name"),
                "events_this_year": len(events),
                "points_by_subject": {k: v for k, v in sorted(by_subject.items()) if v},
                "events_by_type": by_type,
                "recent": events[:10],
            }
        )
        return points


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


class SchoolDaySensor(MCASEntity):
    """What kind of day today is, per the school's own calendar."""

    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "school_day")
        self._attr_name = "School day"

    @property
    def native_value(self):
        return self.coordinator.data.get("day_type") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        return {"next_school_day": self.coordinator.data.get("next_school_day")}


class LessonsTodaySensor(MCASEntity):
    """Lessons timetabled for today."""

    _attr_icon = "mdi:timetable"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "lessons_today")
        self._attr_name = "Lessons today"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("lessons_today") or [])

    @property
    def extra_state_attributes(self) -> dict:
        return {"lessons": self.coordinator.data.get("lessons_today") or []}


class NextLessonSensor(MCASEntity):
    """First lesson of the next timetabled day."""

    _attr_icon = "mdi:chevron-right-circle"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "next_lesson")
        self._attr_name = "Next lesson"

    @property
    def native_value(self):
        lesson = self.coordinator.data.get("next_lesson")
        return lesson.get("subject") if lesson else None

    @property
    def extra_state_attributes(self) -> dict:
        return self.coordinator.data.get("next_lesson") or {}


class ReportsSensor(MCASEntity):
    """School reports available to view."""

    _attr_icon = "mdi:file-document"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "reports")
        self._attr_name = "Reports"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("reports") or [])

    @property
    def extra_state_attributes(self) -> dict:
        return {"reports": self.coordinator.data.get("reports") or []}


class ClubsAndTripsSensor(MCASEntity):
    """Clubs and trips the pupil is enrolled on."""

    _attr_icon = "mdi:bus"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "clubs_and_trips")
        self._attr_name = "Clubs and trips"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("clubs_and_trips") or [])

    @property
    def extra_state_attributes(self) -> dict:
        return {"items": self.coordinator.data.get("clubs_and_trips") or []}
