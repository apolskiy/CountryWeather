import pytest
import yaml
from pathlib import Path

from utils.api_client import ApiClient

_CONFIG_PATH = Path(__file__).parent / "config" / "environments.yaml"
_SUPPORTED_ENVS = ("countries", "weather")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        choices=_SUPPORTED_ENVS,
        default=None,
        help="Restrict execution to a single environment: 'countries' or 'weather'.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "countries: tests targeting the REST Countries API")
    config.addinivalue_line("markers", "weather: tests targeting the Open-Meteo Weather API")


def pytest_runtest_setup(item: pytest.Item) -> None:
    env_flag = item.config.getoption("--env")
    if env_flag is None:
        return
    if not item.get_closest_marker(env_flag):
        pytest.skip(f"excluded by --env={env_flag}")


@pytest.fixture(scope="session")
def _env_configs() -> dict:
    with open(_CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


@pytest.fixture
def api_client_fixture(request: pytest.FixtureRequest, _env_configs: dict) -> ApiClient:
    for env in _SUPPORTED_ENVS:
        if request.node.get_closest_marker(env):
            return ApiClient(_env_configs[env])
    raise KeyError(
        f"Test '{request.node.name}' must carry one of the markers: {_SUPPORTED_ENVS}"
    )
