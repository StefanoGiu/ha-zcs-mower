"""ZCS Lawn Mower Robot entity"""
from __future__ import annotations

from homeassistant.const import (
    ATTR_NAME,
    ATTR_IDENTIFIERS,
    ATTR_LOCATION,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_STATE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    LOGGER,
    DOMAIN,
    MANUFACTURER_DEFAULT,
    MANUFACTURER_MAP,
    ATTRIBUTION,
    ATTR_IMEI,
    ATTR_SERIAL,
    ATTR_CONNECTED,
    ATTR_LAST_COMM,
    ATTR_LAST_SEEN,
    ROBOT_STATES,
)
from .coordinator import ZcsMowerDataUpdateCoordinator


class ZcsMowerEntity(CoordinatorEntity):
    """ZCS Lawn Mower Robot class."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: ZcsMowerDataUpdateCoordinator,
        imei: str,
        name: str,
        entity_type: str,
        entity_key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self.client = coordinator.client
        
        self._imei = imei
        self._name = name
        self._serial = None
        self._model = None
        self._manufacturer = MANUFACTURER_DEFAULT
        
        self._unique_id = slugify(f"{self._imei}_{self._name}")
        
        self._state = 0
        self._available = True
        self._location = {
            ATTR_LATITUDE: None,
            ATTR_LONGITUDE: None,
        }
        self._connected = False
        self._last_communication = None
        self._last_seen = None
        
        self.entity_id = f"{entity_type}.{self._unique_id}"
        self.attrs: dict[str, any] = {
            ATTR_IMEI: self._imei,
            ATTR_CONNECTED: self._connected,
            ATTR_LAST_COMM: self._last_communication,
            ATTR_LAST_SEEN: self._last_seen,
        }

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the icon of the entity."""
        return "mdi:robot-mower"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def device_info(self):
        """Return the device info."""

        return {
            ATTR_IDENTIFIERS: {
                (DOMAIN, self._imei)
            },
            ATTR_NAME: self._name,
            ATTR_MODEL: self._model,
            ATTR_MANUFACTURER: self._manufacturer,
        }

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return Extra Attributes."""
        return self.attrs

    async def async_update(self) -> None:
        """Peform async_update."""
        self._update_handler()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_handler()
        self.async_write_ha_state()

    def _update_handler(self):
        if self._imei in self.coordinator.data:
            robot = self.coordinator.data[self._imei]
            self._state = robot[ATTR_STATE] if robot[ATTR_STATE] < len(ROBOT_STATES) else 0
            self._available = self._state > 0
            if robot[ATTR_LOCATION] is not None:
                self._location = robot[ATTR_LOCATION]
            self._serial = robot[ATTR_SERIAL]
            if (
                self._serial is not None
                and len(self._serial) > 4
            ):
                self._model = self._serial[0:5]
                if self._serial[0:2] in MANUFACTURER_MAP:
                    self._manufacturer = MANUFACTURER_MAP[self._serial[0:2]]
