from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from datetime import datetime
import aiohttp
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    """Set up Hivemapper sensor platform."""
    three_word_name = entry.data["three-word-name"]
    name = entry.data["name"]

    try:
        data = await fetch_data(three_word_name)
    except Exception as e:
        _LOGGER.error(f"Error fetching data for {three_word_name}: {e}")
        data = {}

    async_add_entities([
        HivemapperSensor(f"{DOMAIN} {name} ({three_word_name})", name, three_word_name, data)
    ], update_before_add=True)


async def fetch_data(three_word_name):
    """Fetch data from the Hivemapper API."""
    url = f"https://www.hivemapper.com/api/explorer/user/{three_word_name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                _LOGGER.error(f"User '{three_word_name}' not found.")
            else:
                _LOGGER.error(f"Error fetching data: HTTP {response.status} - {response.reason}")
            return {}


class HivemapperSensor(Entity):
    """Representation of a Hivemapper sensor."""

    def __init__(self, name, driver_name, three_word_name, data):
        """Initialize the sensor."""
        self._name = name
        self._driver_name = driver_name
        self._three_word_name = three_word_name
        self._data = data
        self._state = self._extract_state(data)

    def _extract_state(self, data):
        """Extract the primary state value from the API response."""
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get("kmUploadedByDay", {}).get(today, 0)

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
        """Return additional attributes."""
        return {
            "driver_name": self._driver_name,
            "three_word_name": self._three_word_name,
            **self._data,
        }

    async def async_update(self):
        """Fetch new data from the API."""
        try:
            self._data = await fetch_data(self._three_word_name)
            self._state = self._extract_state(self._data)
        except Exception as e:
            _LOGGER.error(f"Error updating data for {self._three_word_name}: {e}")
