"""Pytest configuration and shared fixtures for the CountryWeather test suite.

Registers the ``--env`` CLI option, declares the ``countries`` and ``weather``
custom markers, and provides the ``api_client_fixture`` function-scoped fixture
that constructs an :class:`~utils.api_client.ApiClient` bound to the correct
environment configuration.

Also injects per-run environment metadata into pytest-html (via the
``pytest_metadata`` hook) and writes an ``environment.properties`` file to
the allure-results directory via ``pytest_sessionfinish``.

Environment filtering is handled by :func:`pytest_collection_modifyitems`:
when ``--env`` is supplied the non-matching items are deselected before the
run begins; when omitted, both marker groups execute in full.
"""

import json
import os
import platform
import sys
from pathlib import Path

import pytest
import yaml

from utils.api_client import ApiClient

_CONFIG_PATH = Path(__file__).parent / "config" / "environments.yaml"
_ALLURE_RESULTS_DIR = Path(__file__).parent / "allure-results"
_MASTER_ENTITIES_PATH = Path(__file__).parent / "test_data" / "master_entities.json"
_SUPPORTED_ENVS = ("countries", "weather")

_DEFAULT_BASE_URL = "https://api.restcountries.com/countries/v5"
_DEFAULT_TEST_ENV = "dev"


def _collect_env_metadata() -> dict:
    """Collect runtime environment metadata for report injection.

    Reads ``BASE_URL`` and ``TEST_ENV`` from the process environment,
    falling back to safe defaults when those variables are absent so the
    suite never crashes at session startup.

    Returns:
        dict: Mapping with keys ``"Operating System"``, ``"Python Version"``,
        ``"Base URL"``, and ``"Test Environment"``.
    """
    return {
        "Operating System": platform.platform(),
        "Python Version": sys.version.split()[0],
        "Base URL": os.environ.get("BASE_URL", _DEFAULT_BASE_URL),
        "Test Environment": os.environ.get("TEST_ENV", _DEFAULT_TEST_ENV),
    }


def pytest_metadata(metadata: dict) -> None:
    """Inject environment metadata into the pytest-html ``Environment`` table.

    Called by the ``pytest-metadata`` plugin once per session. Augments the
    built-in metadata dict so the HTML report's *Environment* section reflects
    the actual runtime context.

    Args:
        metadata (dict): The mutable metadata dict owned by the
            ``pytest-metadata`` plugin.

    Returns:
        None
    """
    metadata.update(_collect_env_metadata())


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write an ``environment.properties`` file to the allure-results directory.

    Creates ``allure-results/`` if it does not yet exist, then serialises all
    collected environment metadata in the Java-properties format expected by the
    Allure report renderer.

    Args:
        session (pytest.Session): The completed pytest session object.
        exitstatus (int): The integer exit code produced by the session.

    Returns:
        None
    """
    _ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    props_path = _ALLURE_RESULTS_DIR / "environment.properties"
    metadata = _collect_env_metadata()
    props_path.write_text(
        "".join(f"{key}={value}\n" for key, value in metadata.items()),
        encoding="utf-8",
    )


def _load_master_entities() -> list[dict]:
    """Load the unified entity dataset from ``test_data/master_entities.json``.

    This file is the single source of truth for all entity information shared
    across the country and weather suites: country common name, ISO 3166-1
    alpha-2 code, geographic region, representative city, and that city's
    latitude/longitude coordinates.

    Returns:
        list[dict]: A list of entity records, each containing the keys
        ``name``, ``cca2``, ``region``, ``city``, ``latitude``, and
        ``longitude``.

    Raises:
        FileNotFoundError: If ``test_data/master_entities.json`` is absent.
        json.JSONDecodeError: If the file does not contain valid JSON.
    """
    with open(_MASTER_ENTITIES_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize any test requesting an ``entity`` argument from the master dataset.

    Implements data-driven testing centrally: every test function (in any
    module) that declares an ``entity`` parameter is automatically parametrized
    over each record in ``test_data/master_entities.json``. Test cases are
    identified by the entity's ``name`` so reports remain cleanly segmented.

    Args:
        metafunc (pytest.Metafunc): The metafunc object for the test function
            being collected, used to inspect requested fixtures and apply
            parametrization.

    Returns:
        None
    """
    if "entity" in metafunc.fixturenames:
        entities = _load_master_entities()
        metafunc.parametrize(
            "entity",
            entities,
            ids=[entity["name"] for entity in entities],
        )


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


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Deselect test items whose marker does not match the active ``--env`` flag.

    When ``--env`` is supplied, items that do not carry the matching marker are
    moved to the deselected set and removed from the run entirely, producing a
    clean ``N selected / M deselected`` summary rather than a list of skips.
    When ``--env`` is omitted, all collected items run unchanged.

    Args:
        config (pytest.Config): The active pytest configuration object.
        items (list[pytest.Item]): The full list of collected test items,
            modified in-place to contain only the selected subset.

    Returns:
        None
    """
    env_flag = config.getoption("--env") or None
    if env_flag is None:
        return
    if env_flag not in _SUPPORTED_ENVS:
        raise ValueError(
            f"--env={env_flag!r} is not valid. Choose from: {_SUPPORTED_ENVS}"
        )

    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []

    for item in items:
        if item.get_closest_marker(env_flag):
            selected.append(item)
        else:
            deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


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
