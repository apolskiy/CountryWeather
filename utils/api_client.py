"""HTTP client wrapper for the CountryWeather test framework.

All network requests issued by the test suite must pass through
:class:`ApiClient`. The wrapper enforces response-time thresholds
configured in ``config/environments.yaml`` using a high-precision timer,
keeping test files free of any performance assertion logic.

For environments that declare an ``auth_env_var`` (such as the REST Countries
v5 API), the client reads the corresponding secret from the process
environment and attaches it as a ``Bearer`` token on every request. The
:meth:`ApiClient.get_objects` helper additionally unwraps the v5
``{"data": {"objects": [...], "meta": {...}}}`` envelope and transparently
paginates list endpoints.
"""

import os
import time
from typing import Any, Optional

import requests


class ApiClient:
    """Environment-scoped HTTP client with auth, response-time gating, and pagination.

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
                ``base_url`` (str), ``max_response_time`` (float),
                ``min_results_count`` (int), ``auth_env_var`` (str or None),
                and ``page_limit`` (int or None). A missing key raises
                :exc:`KeyError` immediately. When ``auth_env_var`` is a
                non-empty string, the named environment variable must be set.

        Raises:
            KeyError: If any required configuration key is absent from
                *env_config*, or if ``auth_env_var`` names an environment
                variable that is not set in the process environment.
        """
        self._base_url: str = env_config["base_url"]
        self._max_response_time: float = env_config["max_response_time"]
        self._min_results_count: int = env_config["min_results_count"]
        self._auth_env_var: Optional[str] = env_config["auth_env_var"]
        self._page_limit: Optional[int] = env_config["page_limit"]
        self._session = requests.Session()

        if self._auth_env_var:
            try:
                token = os.environ[self._auth_env_var]
            except KeyError as exc:
                raise KeyError(
                    f"Required API key environment variable '{self._auth_env_var}' is not set"
                ) from exc
            self._session.headers["Authorization"] = f"Bearer {token}"

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
        ``max_response_time``. The ``Authorization`` header (when configured)
        is applied automatically by the underlying session.

        Args:
            method (str): HTTP method in upper case, e.g. ``"GET"``.
            path (str): URL path to append to the environment ``base_url``,
                e.g. ``"/names.common/germany"``. Pass an empty string to
                target the ``base_url`` itself.
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

    def get_objects(
        self,
        path: str,
        params: Optional[dict] = None,
        *,
        paginate: bool = False,
    ) -> list[dict]:
        """Fetch and unwrap the object list from a v5 ``data.objects`` envelope.

        The REST Countries v5 API wraps every successful payload as
        ``{"data": {"objects": [...], "meta": {...}}}``. This helper issues
        the GET request(s) through :meth:`get` (so auth and response-time
        gating still apply) and returns the flat list of country objects,
        keeping envelope and pagination plumbing out of the test files.

        When *paginate* is ``True`` the helper walks successive pages using
        the configured ``page_limit`` and the ``meta.more`` flag, accumulating
        every object across pages. This is required for list endpoints that
        exceed the API's maximum page size (e.g. the all-countries sweep).

        Args:
            path (str): URL path appended to the environment ``base_url``
                (e.g. ``"/region/europe"``, or ``""`` for all countries).
            params (Optional[dict]): Query parameters merged into each
                request (e.g. ``{"response_fields": "names.common,population"}``).
            paginate (bool): When ``True``, fetch every page by stepping the
                ``offset`` parameter until ``meta.more`` is ``False``.

        Returns:
            list[dict]: The concatenated list of raw country objects.

        Raises:
            KeyError: If *paginate* is requested but ``page_limit`` is not
                configured for this environment.
            requests.HTTPError: Propagated from :meth:`request` on any
                non-2xx response.
        """
        base_params = dict(params or {})

        if not paginate:
            response = self.get(path, params=base_params)
            return response.json()["data"]["objects"]

        if not self._page_limit:
            raise KeyError(
                "Pagination requested but 'page_limit' is not configured for this environment"
            )

        objects: list[dict] = []
        offset = 0
        while True:
            page_params = {**base_params, "limit": self._page_limit, "offset": offset}
            payload = self.get(path, params=page_params).json()["data"]
            objects.extend(payload["objects"])
            if not payload["meta"]["more"]:
                break
            offset += self._page_limit
        return objects
