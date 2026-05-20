"""Typed schema validators for the Open-Meteo Weather API (v1).

Provides :class:`CurrentWeather` and :class:`WeatherSchema` dataclasses that
parse and type-validate raw JSON payloads returned by ``api.open-meteo.com``.
All parsing occurs through :meth:`from_dict` factory methods that perform
explicit field-presence checks before construction.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class CurrentWeather:
    """Structured representation of a current weather observation block.

    Attributes:
        time (str): ISO 8601 timestamp of the observation,
            e.g. ``"2026-05-19T12:00"``.
        interval (int): Data update interval in seconds, typically ``900``.
        temperature (float): Air temperature at 2 m in degrees Celsius.
        windspeed (float): Wind speed at 10 m in km/h.
        winddirection (float): Wind direction in degrees (0–360).
        weathercode (int): WMO weather interpretation code.
        is_day (int): ``1`` if the observation time is during daylight,
            ``0`` if at night.
    """

    time: str
    interval: int
    temperature: float
    windspeed: float
    winddirection: float
    weathercode: int
    is_day: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurrentWeather":
        """Construct a :class:`CurrentWeather` from a raw API payload dict.

        Args:
            data (Dict[str, Any]): The ``current_weather`` sub-object from
                an Open-Meteo forecast response. Must contain all seven
                required keys listed in :class:`CurrentWeather`.

        Returns:
            CurrentWeather: A fully populated and type-cast instance.

        Raises:
            KeyError: If any required field is absent from *data*.
        """
        required = ("time", "interval", "temperature", "windspeed", "winddirection", "weathercode", "is_day")
        for field in required:
            if field not in data:
                raise KeyError(f"Missing mandatory field in 'current_weather': '{field}'")
        return cls(
            time=str(data["time"]),
            interval=int(data["interval"]),
            temperature=float(data["temperature"]),
            windspeed=float(data["windspeed"]),
            winddirection=float(data["winddirection"]),
            weathercode=int(data["weathercode"]),
            is_day=int(data["is_day"]),
        )


@dataclass
class WeatherSchema:
    """Full structural validator for an Open-Meteo forecast response object.

    Attributes:
        latitude (float): Latitude of the resolved grid point in decimal
            degrees.
        longitude (float): Longitude of the resolved grid point in decimal
            degrees.
        timezone (str): IANA timezone name for the location,
            e.g. ``"Europe/Berlin"``, or ``"GMT"`` when not resolved.
        timezone_abbreviation (str): Short timezone label, e.g. ``"CET"``.
        elevation (float): Elevation of the resolved grid point in metres
            above sea level.
        current_weather (CurrentWeather): Parsed current observation block.
    """

    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    elevation: float
    current_weather: CurrentWeather

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherSchema":
        """Construct a :class:`WeatherSchema` from a raw API payload dict.

        Validates that all required top-level fields are present before
        delegating nested construction to :meth:`CurrentWeather.from_dict`.

        Args:
            data (Dict[str, Any]): The top-level JSON object returned by the
                Open-Meteo ``/forecast`` endpoint.

        Returns:
            WeatherSchema: A fully populated and type-cast instance.

        Raises:
            KeyError: If any required field is absent from *data*, or if a
                nested required field is absent from the
                ``current_weather`` sub-object.
        """
        required = ("latitude", "longitude", "timezone", "timezone_abbreviation", "elevation", "current_weather")
        for field in required:
            if field not in data:
                raise KeyError(f"Missing mandatory schema field: '{field}'")
        return cls(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            timezone=str(data["timezone"]),
            timezone_abbreviation=str(data["timezone_abbreviation"]),
            elevation=float(data["elevation"]),
            current_weather=CurrentWeather.from_dict(data["current_weather"]),
        )
