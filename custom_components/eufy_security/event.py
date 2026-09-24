from __future__ import annotations

from datetime import datetime, timezone
import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import EufySecurityDataUpdateCoordinator
from .eufy_security_api.product import Product
from .util import get_device_info

_LOGGER: logging.Logger = logging.getLogger(__package__)

EVENT_TYPE_OPENED = "opened"


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Setup event entities."""
    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]
    entities = [
        EufySecuritySmartDropOpened(coordinator, product)
        for product in coordinator.devices.values()
        if "lastOpenedByType" in product.metadata
    ]
    async_add_entities(entities)


class EufySecuritySmartDropOpened(EventEntity, CoordinatorEntity):
    """Fires once per SmartDrop open, with type, carrier name and count already resolved."""

    _attr_event_types = [EVENT_TYPE_OPENED]
    _attr_icon = "mdi:package-down"

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, product: Product) -> None:
        super().__init__(coordinator)
        self.product = product
        self._attr_unique_id = f"{DOMAIN}_{product.serial_no}_{product.product_type.value}_smartdropOpened"
        self._attr_should_poll = False
        self._attr_name = f"{product.name} Opened"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.product.smartdrop_open_listeners.append(self._on_open)

    async def async_will_remove_from_hass(self) -> None:
        self.product.smartdrop_open_listeners.remove(self._on_open)
        await super().async_will_remove_from_hass()

    @callback
    def _on_open(self, data: dict) -> None:
        open_type = data.get("openedByType")
        metadata = self.product.metadata.get("lastOpenedByType")
        states = metadata.states if metadata is not None and metadata.states is not None else {}
        event_time = data.get("eventTime")
        self._trigger_event(
            EVENT_TYPE_OPENED,
            {
                "open_type": states.get(str(open_type), open_type),
                "pin_name": data.get("openedByName", ""),
                "user_index": data.get("userIndex"),
                "raw_open_type": data.get("rawOpenType"),
                "times_opened": data.get("timesOpened"),
                "event_time": datetime.fromtimestamp(event_time / 1000, tz=timezone.utc).isoformat() if event_time else None,
            },
        )
        self.async_write_ha_state()

    @property
    def device_info(self):
        return get_device_info(self.product)

    @property
    def available(self) -> bool:
        return self.coordinator.available
