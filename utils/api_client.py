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

    # Session-wide timestamp (``time.monotonic``) of the most recently issued
    # request, shared across every per-test instance so the client-side
    # throttle paces requests globally rather than only within one test.
    _last_request_monotonic: float = 0.0

    def __init__(self, env_config: dict) -> None:
        """Initialise the client from a parsed environment configuration block.

        Args:
            env_config (dict): A single environment block loaded from
                ``config/environments.yaml``. Must contain the keys
                ``base_url`` (str), ``max_response_time`` (float),
                ``min_results_count`` (int), ``auth_env_var`` (str or None),
                ``page_limit`` (int or None), ``request_timeout`` (float),
                ``max_retries`` (int), ``retry_backoff`` (float),
                ``retry_statuses`` (list of int), and
                ``min_request_interval`` (float). A missing key raises
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
        self._request_timeout: float = env_config["request_timeout"]
        self._max_retries: int = env_config["max_retries"]
        self._retry_backoff: float = env_config["retry_backoff"]
        self._retry_statuses: frozenset[int] = frozenset(env_config["retry_statuses"])
        self._min_request_interval: float = env_config["min_request_interval"]
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
        """Execute an HTTP request with timeout, retries, and response-time gating.

        Before dispatching, the call is paced against the session-wide
        ``min_request_interval`` so consecutive requests (even across separate
        per-test client instances) never burst past the API's short-window rate
        limit. Constructs the full URL by appending *path* to the configured
        ``base_url`` and issues the request with a hard ``request_timeout``
        (so a stalled connection fails fast rather than hanging indefinitely).
        Transient transport failures (:class:`requests.ConnectionError` and
        :class:`requests.Timeout`) and retryable HTTP statuses (those listed in
        ``retry_statuses``, e.g. ``429`` rate-limiting) are retried up to
        ``max_retries`` times with exponential backoff, honouring a server
        ``Retry-After`` header when present. The round-trip of the *successful*
        attempt is timed with :func:`time.perf_counter` and asserted against
        ``max_response_time``; backoff and failed-attempt time are deliberately
        excluded so the performance gate reflects real server latency. The
        ``Authorization`` header (when configured) is applied automatically by
        the underlying session.

        Args:
            method (str): HTTP method in upper case, e.g. ``"GET"``.
            path (str): URL path to append to the environment ``base_url``,
                e.g. ``"/names.common/germany"``. Pass an empty string to
                target the ``base_url`` itself.
            **kwargs (Any): Additional keyword arguments forwarded verbatim
                to :meth:`requests.Session.request` (e.g. ``params``,
                ``json``, ``headers``). A ``timeout`` may be supplied to
                override the configured ``request_timeout`` for this call.

        Returns:
            requests.Response: The HTTP response object returned by the
            server after a successful status check.

        Raises:
            AssertionError: If the measured response time exceeds the
                configured ``max_response_time`` threshold.
            requests.ConnectionError: If every attempt fails to connect.
            requests.Timeout: If every attempt exceeds ``request_timeout``.
            requests.HTTPError: If the server returns a 4xx or 5xx status
                code, raised by :meth:`~requests.Response.raise_for_status`.
        """
        url = f"{self._base_url}{path}"
        kwargs.setdefault("timeout", self._request_timeout)
        self._throttle()

        for attempt in range(self._max_retries + 1):
            start = time.perf_counter()
            try:
                response = self._session.request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout):
                if attempt >= self._max_retries:
                    raise
                time.sleep(self._retry_backoff * (2 ** attempt))
                continue

            if response.status_code in self._retry_statuses and attempt < self._max_retries:
                time.sleep(self._retry_delay(response, attempt))
                continue

            elapsed = time.perf_counter() - start
            assert elapsed <= self._max_response_time, (
                f"Response time {elapsed:.3f}s exceeded threshold of "
                f"{self._max_response_time}s for {url}"
            )
            response.raise_for_status()
            return response

        raise RuntimeError("unreachable: retry loop exited without returning or raising")

    def _throttle(self) -> None:
        """Pace the next request against the session-wide minimum interval.

        Enforces at least ``min_request_interval`` seconds between the starts of
        consecutive requests by sleeping the remaining gap when the previous
        request was too recent. The reference timestamp is stored on the class,
        so pacing spans every per-test :class:`ApiClient` instance rather than a
        single test. A non-positive interval disables throttling entirely.

        Returns:
            None
        """
        if self._min_request_interval <= 0:
            return
        wait = self._min_request_interval - (
            time.monotonic() - ApiClient._last_request_monotonic
        )
        if wait > 0:
            time.sleep(wait)
        ApiClient._last_request_monotonic = time.monotonic()

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Compute the backoff delay before retrying a retryable response.

        Prefers the server's ``Retry-After`` header (interpreted as a number of
        seconds) when present and numeric; otherwise falls back to exponential
        backoff based on ``retry_backoff``.

        Args:
            response (requests.Response): The retryable response (e.g. a 429).
            attempt (int): Zero-based index of the attempt that just failed.

        Returns:
            float: Number of seconds to sleep before the next attempt.
        """
        header = response.headers.get("Retry-After")
        if header is not None:
            try:
                return float(header)
            except ValueError:
                pass
        return self._retry_backoff * (2 ** attempt)

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
