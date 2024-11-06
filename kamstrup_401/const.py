"""Constants for Kamstrup 401."""

from typing import Final

# Base component constants
NAME: Final = "Kamstrup 401"
DOMAIN: Final = "kamstrup_401"
VERSION: Final = "1.0.0"
MODEL: Final = "401"
MANUFACTURER: Final = "Kamstrup"
ATTRIBUTION: Final = "Data provided by Kamstrup 401 meter"

# Defaults
DEFAULT_NAME: Final = NAME
DEFAULT_BAUDRATE: Final = 300
DEFAULT_SCAN_INTERVAL: Final = 3600
DEFAULT_TIMEOUT: Final = 20.0

# Platforms
SENSOR: Final = "sensor"
PLATFORMS: Final = [SENSOR]
