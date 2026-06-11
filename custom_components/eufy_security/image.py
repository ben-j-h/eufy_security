from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EufySecurityDataUpdateCoordinator
from .entity import EufySecurityEntity
from .eufy_security_api.metadata import Metadata


_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Setup image entities."""
    coordinator: EufySecurityDataUpdateCoordinator = hass.data[DOMAIN][COORDINATOR]
    entities = []
    for product in coordinator.devices.values():
        if product.is_camera is True:
            entities.append(EufySecurityImage(coordinator, Metadata.parse(product, {"name": "camera", "label": "Camera"})))
        if "deliveryThumbnail" in product.metadata:
            entities.append(EufySecurityDeliveryThumbnail(coordinator, Metadata.parse(product, {"name": "deliveryThumbnail", "label": "Delivery Thumbnail"})))
            entities.append(EufySecurityDeliveryCrop(coordinator, Metadata.parse(product, {"name": "deliveryCrop", "label": "Delivery Crop"})))

    async_add_entities(entities)


class EufySecurityImage(ImageEntity, EufySecurityEntity):
    """Base image entity for integration"""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        ImageEntity.__init__(self, coordinator.hass)
        EufySecurityEntity.__init__(self, coordinator, metadata)
        self._attr_name = f"{self.product.name} Event Image"

        # camera image
        self._last_image = None
        if self.product.picture_base64 is not None:
            self._last_image = self.product.picture_bytes

    @property
    def image_last_updated(self) -> datetime | None:
        """The time when the image was last updated."""
        return self.product.image_last_updated

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        if self.product.picture_base64 is not None:
            self._last_image = self.product.picture_bytes
        return self._last_image


class EufySecurityDeliveryThumbnail(ImageEntity, EufySecurityEntity):
    """Delivery thumbnail image entity (video thumbnail from delivery recording)."""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        ImageEntity.__init__(self, coordinator.hass)
        EufySecurityEntity.__init__(self, coordinator, metadata)
        self._attr_name = f"{self.product.name} Delivery Thumbnail"
        self._last_image = None

    @property
    def image_last_updated(self) -> datetime | None:
        return self.product.delivery_thumbnail_last_updated

    async def async_image(self) -> bytes | None:
        if self.product.delivery_thumbnail_base64 is not None:
            self._last_image = self.product.delivery_thumbnail_bytes
        return self._last_image


class EufySecurityDeliveryCrop(ImageEntity, EufySecurityEntity):
    """Delivery crop image entity (AI-detected crop from delivery event)."""

    def __init__(self, coordinator: EufySecurityDataUpdateCoordinator, metadata: Metadata) -> None:
        ImageEntity.__init__(self, coordinator.hass)
        EufySecurityEntity.__init__(self, coordinator, metadata)
        self._attr_name = f"{self.product.name} Delivery Crop"
        self._last_image = None

    @property
    def image_last_updated(self) -> datetime | None:
        return self.product.delivery_crop_last_updated

    async def async_image(self) -> bytes | None:
        if self.product.delivery_crop_base64 is not None:
            self._last_image = self.product.delivery_crop_bytes
        return self._last_image
