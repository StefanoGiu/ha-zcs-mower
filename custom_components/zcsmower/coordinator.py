"""DataUpdateCoordinator for ZCS Lawn Mower Robot."""
from __future__ import annotations

from datetime import (
    timedelta,
    datetime,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    ATTR_NAME,
    ATTR_LOCATION,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_STATE,
    ATTR_SW_VERSION,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    ZcsMowerApiClient,
    ZcsMowerApiAuthenticationError,
    ZcsMowerApiError,
)
from .const import (
    DOMAIN,
    LOGGER,
    API_DATETIME_FORMAT,
    API_ACK_TIMEOUT,
    ATTR_IMEI,
    ATTR_SERIAL,
    ATTR_CONNECTED,
    ATTR_LAST_COMM,
    ATTR_LAST_SEEN,
)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class ZcsMowerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ZCS API."""

    def __init__(
        self,
        mowers: dict,
        hass: HomeAssistant,
        client: ZcsMowerApiClient,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.mowers = mowers
        self.client = client

    async def __aenter__(self):
        """Return Self."""
        return self

    async def __aexit__(self, *excinfo):
        """Close Session before class is destroyed."""
        await self.client._session.close()

    async def _async_update_data(self):
        """Update data via library."""
        try:
            mower_data = {}
            mower_imeis = []
            for _imei, _name in self.mowers.items():
                mower_imeis.append(_imei)
                mower_data[_imei] = {
                    ATTR_NAME: _name,
                    ATTR_IMEI: _imei,
                    ATTR_SERIAL: None,
                    ATTR_SW_VERSION: None,
                    ATTR_STATE: 0,
                    ATTR_LOCATION: None,
                    ATTR_CONNECTED: False,
                    ATTR_LAST_COMM: None,
                    ATTR_LAST_SEEN: None,
                }
            
            await self.client.execute(
                "thing.list",
                {
                    "show": [
                        "id",
                        "key",
                        "name",
                        "connected",
                        "lastSeen",
                        "lastCommunication",
                        "loc",
                        "properties",
                        "alarms",
                        "attrs",
                        "createdOn",
                        "storage",
                        "varBillingPlanCode"
                    ],
                    "hideFields": True,
                    "keys": mower_imeis
                },
            )
            response = await self.client.get_response()
            if "result" in response:
                result_list = response["result"]
                for mower in (
                    mower
                    for mower in result_list
                    if "key" in mower and mower["key"] in mower_data
                ):
                    if "alarms" in mower and "robot_state" in mower["alarms"]:
                        robot_state = mower["alarms"]["robot_state"]
                        mower_data[mower["key"]][ATTR_STATE] = robot_state["state"]
                        # latitude and longitude, not always available
                        if "lat" in robot_state and "lng" in robot_state:
                            mower_data[mower["key"]][ATTR_LOCATION] = {
                                ATTR_LATITUDE: robot_state["lat"],
                                ATTR_LONGITUDE: robot_state["lng"],
                            }
                    if "attrs" in mower:
                        if "robot_serial" in mower["attrs"]:
                            mower_data[mower["key"]][ATTR_SERIAL] = mower["attrs"]["robot_serial"]["value"]
                        if "program_version" in mower["attrs"]:
                            mower_data[mower["key"]][ATTR_SW_VERSION] = mower["attrs"]["program_version"]["value"]
                    if "connected" in mower:
                        mower_data[mower["key"]][ATTR_CONNECTED] = mower["connected"]
                    if "lastCommunication" in mower:
                        mower_data[mower["key"]][ATTR_LAST_COMM] = datetime.strptime(mower["lastCommunication"], API_DATETIME_FORMAT)
                    if "lastSeen" in mower:
                        mower_data[mower["key"]][ATTR_LAST_SEEN] = datetime.strptime(mower["lastSeen"], API_DATETIME_FORMAT)

            # TODO
            LOGGER.debug("_async_update_data")
            LOGGER.debug(mower_data)

            return mower_data
        except ZcsMowerApiAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except ZcsMowerApiError as exception:
            raise UpdateFailed(exception) from exception

    async def async_wake_up(
        self,
        imei: str,
    ) -> bool:
        """Send command wake_up to lawn nower."""
        LOGGER.debug(f"wake_up: {imei}")
        try:
            return await self.client.execute(
                "sms.send",
                {
                    "coding": "SEVEN_BIT",
                    "imei": imei,
                    "message": "UP",
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False

    async def async_set_profile(
        self,
        imei: str,
        profile: int,
    ) -> bool:
        """Send command set_profile to lawn nower."""
        LOGGER.debug(f"set_profile: {imei}")
        try:
            await self.async_wake_up(imei)
            return await self.client.execute(
                "method.exec",
                {
                    "method": "set_profile",
                    "imei": imei,
                    "params": {
                        "profile": (profile - 1),
                    },
                    "ackTimeout": API_ACK_TIMEOUT,
                    "singleton": True,
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False

    async def async_work_until(
        self,
        imei: str,
        area: int,
        hours: int,
        minutes: int,
    ) -> bool:
        """Send command work_until to lawn nower."""
        LOGGER.debug(f"work_until: {imei}")
        try:
            await self.async_wake_up(imei)
            return await self.client.execute(
                "method.exec",
                {
                    "method": "work_until",
                    "imei": imei,
                    "params": {
                        "area": (area - 1),
                        "hh": hours,
                        "mm": minutes,
                    },
                    "ackTimeout": API_ACK_TIMEOUT,
                    "singleton": True,
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False

    async def async_border_cut(
        self,
        imei: str,
    ) -> bool:
        """Send command border_cut to lawn nower."""
        LOGGER.debug(f"border_cut: {imei}")
        try:
            await self.async_wake_up(imei)
            return await self.client.execute(
                "method.exec",
                {
                    "method": "border_cut",
                    "imei": imei,
                    "ackTimeout": API_ACK_TIMEOUT,
                    "singleton": True,
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False

    async def async_charge_until(
        self,
        imei: str,
        hours: int,
        minutes: int,
        weekday: int,
    ) -> bool:
        """Send command charge_until to lawn nower."""
        LOGGER.debug(f"charge_until: {imei}")
        try:
            await self.async_wake_up(imei)
            return await self.client.execute(
                "method.exec",
                {
                    "method": "charge_until",
                    "imei": imei,
                    "params": {
                        "hh": hours,
                        "mm": minutes,
                        "weekday": weekday,
                    },
                    "ackTimeout": API_ACK_TIMEOUT,
                    "singleton": True,
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False

    async def async_trace_position(
        self,
        imei: str,
    ) -> bool:
        """Send command trace_position to lawn nower."""
        LOGGER.debug(f"trace_position: {imei}")
        try:
            await self.async_wake_up(imei)
            return await self.client.execute(
                "method.exec",
                {
                    "method": "trace_position",
                    "imei": imei,
                    "ackTimeout": API_ACK_TIMEOUT,
                    "singleton": True,
                },
            )
        except Exception as exception:
            LOGGER.exception(exception)
        return False
