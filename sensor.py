from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from datetime import datetime
import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the sensor platform for the integration."""
    three_word_name = entry.data["three-word-name"]
    name = entry.data["name"]

    try:
        data = await fetch_data(three_word_name)
    except Exception as e:
        _LOGGER.error(f"Error fetching data for {three_word_name}: {e}")
        data = {}

    sensors = []

    # Process 'user' section
    user = data.get("user", {})
    for key, value in user.items():
        if isinstance(value, (str, int, float)):  # Only include simple types
            unique_id = f"hivemapper_{name}_{three_word_name}_{key.lower()}"
            entity_id = f"sensor.hivemapper_{name}_{three_word_name}_{key.lower()}"
            sensor_name = f"Hivemapper {name.capitalize()} {three_word_name} {key.capitalize()}"
            _LOGGER.debug(f"Creating user sensor: {unique_id=}, {sensor_name=}, {entity_id=}")
            sensors.append(
                HivemapperSensor(
                    unique_id,
                    sensor_name,
                    value,
                    {},
                    entity_id=entity_id
                )
            )

    # Process 'stats' section
    stats = data.get("stats", {})
    for key, value in stats.items():
        if isinstance(value, dict):  # For nested data
            unique_id = f"hivemapper_{name}_{three_word_name}_{key.lower()}"
            entity_id = f"sensor.hivemapper_{name}_{three_word_name}_{key.lower()}"
            sensor_name = f"Hivemapper {name.capitalize()} {three_word_name} {key.capitalize()}"
            summarized_value = summarize_data(value)
            _LOGGER.debug(f"Creating stats sensor (dict): {unique_id=}, {sensor_name=}, {entity_id=}, {summarized_value=}")
            sensors.append(
                HivemapperSensor(
                    unique_id,
                    sensor_name,
                    summarized_value,
                    value,
                    entity_id=entity_id
                )
            )
        else:  # For simple metrics
            unique_id = f"hivemapper_{name}_{three_word_name}_{key.lower()}"
            entity_id = f"sensor.hivemapper_{name}_{three_word_name}_{key.lower()}"
            sensor_name = f"Hivemapper {name.capitalize()} {three_word_name} {key.capitalize()}"
            _LOGGER.debug(f"Creating stats sensor (simple): {unique_id=}, {sensor_name=}, {entity_id=}, {value=}")
            sensors.append(
                HivemapperSensor(
                    unique_id,
                    sensor_name,
                    value,
                    {},
                    entity_id=entity_id
                )
            )

    # Add the sensors to Home Assistant
    async_add_entities(sensors, update_before_add=True)


async def fetch_data(three_word_name: str):
    """Fetch data from the Hivemapper API."""
    url = f"https://www.hivemapper.com/api/explorer/user/{three_word_name}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    _LOGGER.debug(f"Successfully fetched data for {three_word_name}")
                    return await response.json()
                elif response.status == 404:
                    _LOGGER.error(f"User '{three_word_name}' not found.")
                else:
                    _LOGGER.error(f"Error fetching data: HTTP {response.status} - {response.reason}")
    except Exception as e:
        _LOGGER.error(f"Failed to fetch data for '{three_word_name}': {e}")

    return {}


def summarize_data(data):
    """Summarize nested data by returning the most recent or total value."""
    today = datetime.now().strftime("%Y-%m-%d")
    if today in data:
        return data[today]  # Return today's data if available
    elif isinstance(data, dict):
        last_date = sorted(data.keys())[-1]
        return data[last_date]
    return 0  # Default to 0 if no data is available


class HivemapperSensor(Entity):
    """Representation of a sensor for the integration."""

    def __init__(self, unique_id: str, name: str, state, attributes: dict, entity_id: str = None):
        """Initialize the sensor."""
        self._unique_id = unique_id
        self._name = name
        self._state = state
        self._attributes = attributes
        self.entity_id = entity_id

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        return self._attributes

    async def async_update(self):
        """Update the sensor with the latest data."""
        _LOGGER.debug(f"Updating sensor: {self._name}")
