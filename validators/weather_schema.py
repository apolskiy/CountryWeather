"""Typed schema validators for the Open-Meteo Weather API (v1).

Provides :class:`CurrentWeather`, :class:`WeatherHourlyData`,
:class:`WeatherSchema`, and :class:`WeatherForecastSchema` dataclasses that
parse and type-validate raw JSON payloads returned by ``api.open-meteo.com``.
All parsing occurs through :meth:`from_dict` factory methods that perform
explicit field-presence checks before construction.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


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
class WeatherHourlyData:
    """Structured representation of an hourly forecast data block.

    Validates the ``hourly`` sub-object returned when the ``hourly``
    query parameter is included in a ``/forecast`` request.

    Attributes:
        time (List[str]): Ordered list of ISO 8601 hourly timestamps.
        temperature_2m (List[float]): Air temperature at 2 m in degrees
            Celsius for each corresponding timestamp entry.
    """

    time: List[str]
    temperature_2m: List[float]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherHourlyData":
        """Construct a :class:`WeatherHourlyData` from a raw API payload dict.

        Args:
            data (Dict[str, Any]): The ``hourly`` sub-object from an
                Open-Meteo forecast response. Must contain ``"time"`` and
                ``"temperature_2m"`` keys, each holding a list of values.

        Returns:
            WeatherHourlyData: A fully populated and type-cast instance.

        Raises:
            KeyError: If ``"time"`` or ``"temperature_2m"`` is absent from
                *data*.
        """
        for field in ("time", "temperature_2m"):
            if field not in data:
                raise KeyError(f"Missing mandatory field in 'hourly': '{field}'")
        return cls(
            time=[str(timestamp) for timestamp in data["time"]],
            temperature_2m=[float(reading) for reading in data["temperature_2m"]],
        )


@dataclass
class WeatherSchema:
    """Full structural validator for an Open-Meteo current-weather response.

    Used for responses that include only ``current_weather=true``. For
    responses that additionally include hourly data, use
    :class:`WeatherForecastSchema`.

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


@dataclass
class WeatherForecastSchema:
    """Full structural validator for a combined current-weather + hourly response.

    Used when the ``/forecast`` request includes both ``current_weather=true``
    and an ``hourly`` field parameter (e.g. ``hourly=temperature_2m``).
    For current-weather-only responses, use :class:`WeatherSchema`.

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
        hourly (WeatherHourlyData): Parsed hourly temperature forecast block.
    """

    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    elevation: float
    current_weather: CurrentWeather
    hourly: WeatherHourlyData

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherForecastSchema":
        """Construct a :class:`WeatherForecastSchema` from a raw API payload dict.

        Validates all required top-level fields before delegating nested
        construction to :meth:`CurrentWeather.from_dict` and
        :meth:`WeatherHourlyData.from_dict`.

        Args:
            data (Dict[str, Any]): The top-level JSON object returned by the
                Open-Meteo ``/forecast`` endpoint when both
                ``current_weather=true`` and an ``hourly`` parameter are
                supplied.

        Returns:
            WeatherForecastSchema: A fully populated and type-cast instance.

        Raises:
            KeyError: If any required field is absent from *data*, or if a
                nested required field is absent from either the
                ``current_weather`` or ``hourly`` sub-objects.
        """
        required = (
            "latitude", "longitude", "timezone", "timezone_abbreviation",
            "elevation", "current_weather", "hourly",
        )
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
            hourly=WeatherHourlyData.from_dict(data["hourly"]),
        )
