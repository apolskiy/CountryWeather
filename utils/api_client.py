"""HTTP client wrapper for the CountryWeather test framework.

All network requests issued by the test suite must pass through
:class:`ApiClient`. The wrapper enforces response-time thresholds
configured in ``config/environments.yaml`` using a high-precision timer,
keeping test files free of any performance assertion logic.
"""

import time
from typing import Any

import requests


class ApiClient:
    """Environment-scoped HTTP client with built-in response-time gating.

    Wraps :class:`requests.Session` and automatically asserts that every
    request completes within the ``max_response_time`` threshold sourced
    from ``config/environments.yaml``. Instantiated per-test by the
    ``api_client_fixture`` fixture in ``conftest.py``.

    Attributes:
        min_results_count (int): Minimum number of results a list endpoint
            must return, sourced from the active environment configuration.
    """

    def __init__(self, env_config: dict) -> None:
        """Initialise the client from a parsed environment configuration block.

        Args:
            env_config (dict): A single environment block loaded from
                ``config/environments.yaml``. Must contain the keys
                ``base_url`` (str), ``max_response_time`` (float), and
                ``min_results_count`` (int). A missing key raises
                :exc:`KeyError` immediately.

        Raises:
            KeyError: If any required configuration key is absent from
                *env_config*.
        """
        self._base_url: str = env_config["base_url"]
        self._max_response_time: float = env_config["max_response_time"]
        self._min_results_count: int = env_config["min_results_count"]
        self._session = requests.Session()

    @property
    def min_results_count(self) -> int:
        """Minimum result count threshold from the active environment config.

        Returns:
            int: The ``min_results_count`` value sourced from
            ``config/environments.yaml`` for the current environment.
        """
        return self._min_results_count

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Execute an HTTP request and enforce the response-time threshold.

        Constructs the full URL by appending *path* to the configured
        ``base_url``, times the round-trip with :func:`time.perf_counter`,
        and asserts that the elapsed time does not exceed
        ``max_response_time``.

        Args:
            method (str): HTTP method in upper case, e.g. ``"GET"``.
            path (str): URL path to append to the environment ``base_url``,
                e.g. ``"/name/germany"``.
            **kwargs (Any): Additional keyword arguments forwarded verbatim
                to :meth:`requests.Session.request` (e.g. ``params``,
                ``json``, ``headers``).

        Returns:
            requests.Response: The HTTP response object returned by the
            server after a successful status check.

        Raises:
            AssertionError: If the measured response time exceeds the
                configured ``max_response_time`` threshold.
            requests.HTTPError: If the server returns a 4xx or 5xx status
                code, raised by :meth:`~requests.Response.raise_for_status`.
        """
        url = f"{self._base_url}{path}"
        start = time.perf_counter()
        response = self._session.request(method, url, **kwargs)
        elapsed = time.perf_counter() - start
        assert elapsed <= self._max_response_time, (
            f"Response time {elapsed:.3f}s exceeded threshold of {self._max_response_time}s for {url}"
        )
        response.raise_for_status()
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """Issue a GET request through the client wrapper.

        Args:
            path (str): URL path to append to the environment ``base_url``.
            **kwargs (Any): Additional keyword arguments forwarded to
                :meth:`request` (e.g. ``params``).

        Returns:
            requests.Response: The HTTP response object from :meth:`request`.
        """
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """Issue a POST request through the client wrapper.

        Args:
            path (str): URL path to append to the environment ``base_url``.
            **kwargs (Any): Additional keyword arguments forwarded to
                :meth:`request` (e.g. ``json``, ``data``).

        Returns:
            requests.Response: The HTTP response object from :meth:`request`.
        """
        return self.request("POST", path, **kwargs)
