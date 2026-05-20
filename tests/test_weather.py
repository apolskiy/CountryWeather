"""Functional test suite for the Open-Meteo Weather API (api.open-meteo.com/v1).

Covers the following endpoint contracts:

* ``GET /forecast?latitude=…&longitude=…&current_weather=true``
  — current observation schema and physical-range validation.
* ``GET /forecast?latitude=…&longitude=…&current_weather=true&hourly=temperature_2m``
  — combined current-weather and hourly forecast validation.

Parametrized coordinates for the existing suite are loaded from
``test_data/coordinates.json``; the hourly forecast suite is parametrized
from ``test_data/cities.json``. Every response is validated through a schema
class from :mod:`validators.weather_schema`.

Run this suite exclusively::

    pytest --env=weather
"""

import json
import logging
import pytest
import allure
from pathlib import Path

from utils.api_client import ApiClient
from validators.weather_schema import WeatherForecastSchema, WeatherSchema

_COORDINATES = json.loads((Path(__file__).parent.parent / "test_data" / "coordinates.json").read_text())
_CITIES = json.loads((Path(__file__).parent.parent / "test_data" / "cities.json").read_text())

logger = logging.getLogger(__name__)


@pytest.mark.weather
@allure.epic("Environment-Driven API Validation")
@allure.feature("Open-Meteo Weather API")
class TestWeather:
    """Test suite for the Open-Meteo Weather API forecast endpoint.

    ``test_current_weather_by_coordinates`` is parametrized over
    ``test_data/coordinates.json`` and validates
    :class:`~validators.weather_schema.WeatherSchema`.

    ``test_forecast_by_city`` is parametrized over
    ``test_data/cities.json`` and validates
    :class:`~validators.weather_schema.WeatherForecastSchema`, which covers
    both the ``current_weather`` and ``hourly`` response blocks.
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

        Raises:
            AssertionError: If schema validation fails or any physical-range
                or coordinate-tolerance assertion does not hold.
        """
        try:
            with allure.step(f"GET /forecast for {location['city']} ({location['latitude']}, {location['longitude']})"):
                response = api_client_fixture.get("/forecast", params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current_weather": "true",
                })
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

            with allure.step("Validate full WeatherSchema"):
                validated = WeatherSchema.from_dict(response.json())
                logger.info(
                    "Schema validated — timezone=%s, temperature=%.1f°C",
                    validated.timezone,
                    validated.current_weather.temperature,
                )

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
        except AssertionError as exc:
            logger.error("test_current_weather_by_coordinates failed for %s: %s", location["city"], exc)
            raise

    @allure.story("Hourly Forecast by City — Schema, Temperature Range, and Entry Count")
    @pytest.mark.parametrize("city", _CITIES, ids=[c["city"] for c in _CITIES])
    def test_forecast_by_city(self, api_client_fixture: ApiClient, city: dict) -> None:
        """Verify schema correctness and forecast integrity for city-based hourly lookups.

        Issues a ``GET /forecast`` request (full URL: ``/v1/forecast``) with
        both ``current_weather=true`` and ``hourly=temperature_2m``, then
        validates the full response through
        :class:`~validators.weather_schema.WeatherForecastSchema`. Asserts
        that the current temperature is within the physically valid range of
        -80 °C to 60 °C, that the hourly dataset contains at least one entry,
        and that the ``timezone`` field is a non-empty string.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            city (dict): A single entry from ``test_data/cities.json``
                containing ``city``, ``latitude``, and ``longitude`` keys.

        Returns:
            None

        Raises:
            AssertionError: If schema validation fails or any of the
                temperature-range, hourly-count, or timezone assertions do
                not hold.
        """
        try:
            with allure.step(f"GET /forecast for {city['city']} ({city['latitude']}, {city['longitude']})"):
                response = api_client_fixture.get("/forecast", params={
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "current_weather": "true",
                    "hourly": "temperature_2m",
                })
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

            with allure.step("Validate full WeatherForecastSchema"):
                validated = WeatherForecastSchema.from_dict(response.json())
                logger.info(
                    "Schema validated — city=%s, timezone=%s, hourly_entries=%d",
                    city["city"],
                    validated.timezone,
                    len(validated.hourly.temperature_2m),
                )

            with allure.step("Assert current temperature is within valid range (-80 °C to 60 °C)"):
                temp = validated.current_weather.temperature
                assert -80.0 <= temp <= 60.0, (
                    f"Temperature {temp}°C out of range [-80, 60] for {city['city']}"
                )

            with allure.step("Assert hourly forecast contains at least one entry"):
                hourly_count = len(validated.hourly.temperature_2m)
                assert hourly_count > 0, (
                    f"Expected at least 1 hourly entry for {city['city']}, got {hourly_count}"
                )

            with allure.step("Assert timezone field is a non-empty string"):
                assert validated.timezone != "", (
                    f"Empty timezone field for {city['city']}"
                )
        except AssertionError as exc:
            logger.error("test_forecast_by_city failed for %s: %s", city["city"], exc)
            raise
