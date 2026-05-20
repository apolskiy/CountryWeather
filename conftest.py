"""Pytest configuration and shared fixtures for the CountryWeather test suite.

Registers the ``--env`` CLI option, declares the ``countries`` and ``weather``
custom markers, and provides the ``api_client_fixture`` function-scoped fixture
that constructs an :class:`~utils.api_client.ApiClient` bound to the correct
environment configuration.

Environment filtering follows the pattern documented in ``CLAUDE_LOG.md``:
a :func:`pytest_runtest_setup` hook inspects the ``--env`` flag per item so
that both marker groups execute by default when the flag is omitted.
"""

import pytest
import yaml
from pathlib import Path

from utils.api_client import ApiClient

_CONFIG_PATH = Path(__file__).parent / "config" / "environments.yaml"
_SUPPORTED_ENVS = ("countries", "weather")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the ``--env`` command-line option.

    Args:
        parser (pytest.Parser): The pytest argument parser provided by
            the framework during option registration.

    Returns:
        None
    """
    parser.addoption(
        "--env",
        action="store",
        choices=_SUPPORTED_ENVS,
        default=None,
        help="Restrict execution to a single environment: 'countries' or 'weather'.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers to suppress ``PytestUnknownMarkWarning``.

    Args:
        config (pytest.Config): The active pytest configuration object.

    Returns:
        None
    """
    config.addinivalue_line("markers", "countries: tests targeting the REST Countries API")
    config.addinivalue_line("markers", "weather: tests targeting the Open-Meteo Weather API")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests whose marker does not match the active ``--env`` flag.

    When ``--env`` is supplied, any test item that does not carry the
    matching marker is skipped before setup begins. When ``--env`` is
    omitted, all items run regardless of marker.

    Args:
        item (pytest.Item): The test item about to enter the setup phase.

    Returns:
        None
    """
    env_flag = item.config.getoption("--env")
    if env_flag is None:
        return
    if not item.get_closest_marker(env_flag):
        pytest.skip(f"excluded by --env={env_flag}")


@pytest.fixture(scope="session")
def _env_configs() -> dict:
    """Load and cache the full ``config/environments.yaml`` for the session.

    Returns:
        dict: The complete parsed YAML structure keyed by environment name
        (``"countries"`` and ``"weather"``).
    """
    with open(_CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def api_client_fixture(request: pytest.FixtureRequest, _env_configs: dict) -> ApiClient:
    """Provide a function-scoped :class:`ApiClient` bound to the test's environment.

    Inspects the closest pytest marker on the requesting test node to determine
    which environment block to read from *_env_configs*, then constructs a
    fresh :class:`ApiClient` instance for each test.

    Args:
        request (pytest.FixtureRequest): Pytest fixture request object used
            to inspect the active test node and its markers.
        _env_configs (dict): Session-scoped dict of all environment
            configurations parsed from ``config/environments.yaml``.

    Returns:
        ApiClient: A fully initialised client configured for the environment
        matching the test's marker.

    Raises:
        KeyError: If the test node carries none of the supported environment
            markers (``"countries"`` or ``"weather"``).
    """
    for env in _SUPPORTED_ENVS:
        if request.node.get_closest_marker(env):
            return ApiClient(_env_configs[env])
    raise KeyError(
        f"Test '{request.node.name}' must carry one of the markers: {_SUPPORTED_ENVS}"
    )
