"""Functional test suite for the Open-Meteo Weather API (api.open-meteo.com/v1).

Covers the current-weather endpoint contract:

* ``GET /forecast?latitude=…&longitude=…&current_weather=true``

All test parameters are loaded from ``test_data/coordinates.json`` at
collection time. Every response is validated through
:class:`~validators.weather_schema.WeatherSchema` to enforce strict
structural and type correctness, followed by physical-range sanity checks
on the returned observation values.

Run this suite exclusively::

    pytest --env=weather
"""

import json
import pytest
import allure
from pathlib import Path

from utils.api_client import ApiClient
from validators.weather_schema import WeatherSchema

_COORDINATES = json.loads((Path(__file__).parent / "test_data" / "coordinates.json").read_text())


@pytest.mark.weather
@allure.epic("Environment-Driven API Validation")
@allure.feature("Open-Meteo Weather API")
class TestWeather:
    """Test class for the Open-Meteo Weather API forecast endpoint.

    Each test method is parametrized over the coordinate dataset in
    ``test_data/coordinates.json`` and validates the full
    :class:`~validators.weather_schema.WeatherSchema` on every response.
    """

    @allure.story("Current Weather by Coordinates — Schema and Data Integrity")
    @pytest.mark.parametrize("location", _COORDINATES, ids=[c["city"] for c in _COORDINATES])
    def test_current_weather_by_coordinates(
        self, api_client_fixture: ApiClient, location: dict
    ) -> None:
        """Verify schema correctness and data integrity for coordinate-based weather lookups.

        Issues a ``GET /forecast`` request with ``current_weather=true`` and
        asserts that the response passes full
        :class:`~validators.weather_schema.WeatherSchema` validation, that the
        returned coordinates fall within the expected grid-snapping tolerance,
        and that all observation values are within physically valid ranges.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            location (dict): A single entry from ``test_data/coordinates.json``
                containing ``city``, ``latitude``, and ``longitude`` keys.

        Returns:
            None
        """
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current_weather": "true",
        }

        with allure.step(f"GET /forecast for {location['city']} ({location['latitude']}, {location['longitude']})"):
            response = api_client_fixture.get("/forecast", params=params)

        with allure.step("Validate full response schema"):
            validated = WeatherSchema.from_dict(response.json())

        with allure.step("Assert returned coordinates match request within snapping tolerance"):
            assert abs(validated.latitude - location["latitude"]) < 1.0, (
                f"Latitude mismatch: requested {location['latitude']}, got {validated.latitude}"
            )
            assert abs(validated.longitude - location["longitude"]) < 1.0, (
                f"Longitude mismatch: requested {location['longitude']}, got {validated.longitude}"
            )

        with allure.step("Assert current weather values are within physically valid ranges"):
            cw = validated.current_weather
            assert -90.0 <= cw.temperature <= 60.0, f"Temperature out of range: {cw.temperature}"
            assert cw.windspeed >= 0.0, f"Negative windspeed: {cw.windspeed}"
            assert 0.0 <= cw.winddirection <= 360.0, f"Wind direction out of range: {cw.winddirection}"
            assert cw.is_day in (0, 1), f"is_day must be 0 or 1, got {cw.is_day}"
            assert cw.interval > 0, f"Non-positive interval: {cw.interval}"
