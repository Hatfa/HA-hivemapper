import logging
import re
import aiohttp
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback

DEFAULT_SCAN_INTERVAL = 300

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("name"): str,
        vol.Required("three-word-name"): str,
        vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
    }
)

# set the base api url 
API_BASE_URL = "https://www.hivemapper.com/api/explorer/user/"

_LOGGER = logging.getLogger(__name__)

class HivemapperConfigFlow(config_entries.ConfigFlow, domain="hivemapper"):
    """Handle a config flow for Hivemapper."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # get user inputs on first form page
            name = user_input.get("name")
            three_word_name = user_input.get("three-word-name")
            scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)

            # Validate three-word-name format
            if not self._is_valid_three_word_name(three_word_name):
                errors["three-word-name"] = "Invalid format. Must be lowercase words separated by hyphens."

            # Check if three-word-name is already added
            if self._is_three_word_name_duplicate(three_word_name):
                errors["three-word-name"] = "This three-word name has already been added."

            # Validate scan interval
            if scan_interval <= 0:
                errors["scan_interval"] = "Must be a positive integer."

            if not errors:
                # Make the API call to check for data. This helps verify potential typos.
                api_status, api_data = await self._check_api_for_data(three_word_name)
                if api_status == 200 and api_data:
                    # If data is available and contains "stats", proceed to create the entry
                    if "stats" in api_data:
                        if not name:
                            name = await self._generate_unique_driver_name()
                        user_input["name"] = name
                        return self.async_create_entry(
                            title=f"{name} {three_word_name}",
                            data=user_input,
                        )
                    else:
                        # If "stats" is not available in the data, proceed to confirmation
                        self.context["user_input"] = user_input
                        return await self.async_step_confirmation()

                else:
                    # If no valid data is available, proceed to confirmation
                    self.context["user_input"] = user_input
                    return await self.async_step_confirmation()

        # Show the form with any errors
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
     # Allow user to add three-word-name without data as newly created users will have none
    async def async_step_confirmation(self, user_input=None):
        """Confirmation step for proceeding without API data."""
        errors = {}
      
        if user_input is not None:
            if not user_input.get("confirm"):
                # If checkbox is unchecked, abort the flow
                return self.async_abort(reason="user_declined")

            # Create the entry regardless of API data
            original_input = self.context.get("user_input", {})
            name = original_input.get("name") or await self._generate_unique_driver_name()
            original_input["name"] = name
            return self.async_create_entry(
                title=f"{name} {original_input['three-word-name']}",
                data=original_input,
            )
    # Retrieve the three-word-name from user input to display for verification
        three_word_name = self.context["user_input"]["three-word-name"]

        # Add the confirmation message as an error
        errors["confirm"] = f"Error! The username: '{three_word_name}' entered is either incorrect or the user is new and not collected any data yet. Confirm if you wish to add the user anyways."
        
        # Ask the user to confirm with the error message above the checkbox
        return self.async_show_form(
            step_id="confirmation",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def _check_api_for_data(self, three_word_name):
        """Make the actual API call to check for data."""
        url = f"{API_BASE_URL}{three_word_name}"  # Construct the full URL with the three-word-name
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if "stats" is in the response data
                        if "stats" in data:
                            return 200, data  # Return status 200 and the data if "stats" is available
                    else:
                        _LOGGER.error(f"API request failed with status code: {response.status}")
                        return response.status, None
        except Exception as e:
            _LOGGER.error(f"Error while fetching data from API: {e}")
            return 500, None  # Return 500 if there's an error with the request

        return 404, None  # Default to 404 if no valid data or "stats" is not found

    async def _generate_unique_driver_name(self):
        """Generate a unique driver name."""
        existing_names = {entry.data.get("name", "") for entry in self._async_current_entries()}
        count = 1
        while f"Driver_{count}" in existing_names:
            count += 1
        return f"Driver_{count}"

    def _is_three_word_name_duplicate(self, three_word_name):
        """Check if the three-word name already exists."""
        for entry in self._async_current_entries():
            if entry.data.get("three-word-name") == three_word_name:
                return True
        return False

    @staticmethod
    def _is_valid_three_word_name(name):
        """Validate the three-word name format."""
        pattern = r"^[a-z]+(-[a-z]+){2}$"  # Regex pattern for lowercase hyphenated words
        return bool(re.match(pattern, name))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow for this handler."""
        return HivemapperOptionsFlowHandler(config_entry)


class HivemapperOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Hivemapper integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        options_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval", default=self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                ): int,
            }
        )

        if user_input is not None:
            # Validate scan interval
            if user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL) <= 0:
                return self.async_show_form(
                    step_id="init",
                    data_schema=options_schema,
                    errors={"scan_interval": "Must be a positive integer."},
                )

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=options_schema)