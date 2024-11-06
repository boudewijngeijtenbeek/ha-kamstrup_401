"""Sensor platform for kamstrup_401."""
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
#from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KamstrupUpdateCoordinator
from .const import DEFAULT_NAME, DOMAIN

DESCRIPTIONS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="6.8",
        name="Thermal Energy",
        icon="mdi:radiator",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="6.26",
        name="Volume",
        icon="mdi:water",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="6.31",
        name="Hour Counter",
        icon="mdi:timer-sand",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kamstrup sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[KamstrupSensor] = []

    # Add all meter sensors described above.
    for description in DESCRIPTIONS:
        entities.append(
            KamstrupMeterSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                description=description,
            )
        )
        
    # Add a "gas" sensor.
    entities.append(
        KamstrupGasSensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            description=SensorEntityDescription(
                key="gas",
                name="Thermal Energy to Gas",
                icon="mdi:gas-burner",
                #native_unit_of_measurement=VOLUME_CUBIC_METERS,
                native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
                device_class=SensorDeviceClass.GAS,
                state_class=SensorStateClass.TOTAL_INCREASING,
                entity_registry_enabled_default=False,
            ),
        )
    )

    async_add_entities(entities)


class KamstrupSensor(CoordinatorEntity[KamstrupUpdateCoordinator], SensorEntity):
    """Defines a Kamstrup sensor."""

    def __init__(
        self,
        coordinator: KamstrupUpdateCoordinator,
        entry_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Kamstrup sensor."""
        super().__init__(coordinator=coordinator)

        self.entity_id = f"{SENSOR_DOMAIN}.{DEFAULT_NAME}_{description.name}".lower()
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}-{DEFAULT_NAME} {self.name}"
        self._attr_device_info = coordinator.device_info


class KamstrupMeterSensor(KamstrupSensor):
    """Defines a Kamstrup meter sensor."""

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.coordinator.register_command(self.entity_description.key)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        self.coordinator.unregister_command(self.entity_description.key)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data[self.entity_description.key]:
            return self.coordinator.data[self.entity_description.key].get("value", None)

        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor, if any."""
        if self.coordinator.data and self.coordinator.data[self.entity_description.key]:
            return self.coordinator.data[self.entity_description.key].get("unit", None)

        return None
        
        
class KamstrupGasSensor(KamstrupSensor):
    """Defines a Kamstrup gas sensor."""

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data["6.8"]:
            return self.coordinator.data["6.8"].get("value", None)

        return None