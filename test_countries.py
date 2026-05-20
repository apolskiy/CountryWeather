"""Functional test suite for the REST Countries API (restcountries.com/v3.1).

Covers two endpoint contracts:

* ``GET /name/{name}`` — country lookup by common name.
* ``GET /alpha/{cca2}`` — country lookup by ISO 3166-1 alpha-2 code.

All test parameters are loaded from ``test_data/countries.json`` at
collection time. Every response is validated through
:class:`~validators.country_schema.CountrySchema` to enforce strict
structural and type correctness.

Run this suite exclusively::

    pytest --env=countries
"""

import json
import pytest
import allure
from pathlib import Path

from utils.api_client import ApiClient
from validators.country_schema import CountrySchema

_COUNTRIES = json.loads((Path(__file__).parent / "test_data" / "countries.json").read_text())


@pytest.mark.countries
@allure.epic("Environment-Driven API Validation")
@allure.feature("REST Countries API")
class TestCountries:
    """Test class for the REST Countries API endpoints.

    Each test method is parametrized over the dataset in
    ``test_data/countries.json`` and validates the full
    :class:`~validators.country_schema.CountrySchema` on every response.
    """

    @allure.story("Country Lookup by Name — Schema and Count")
    @pytest.mark.parametrize("country", _COUNTRIES, ids=[c["name"] for c in _COUNTRIES])
    def test_country_by_name(self, api_client_fixture: ApiClient, country: dict) -> None:
        """Verify schema correctness and result count for name-based lookups.

        Issues a ``GET /name/{name}`` request and asserts that the response
        list meets the configured minimum length and that the first result
        passes full :class:`~validators.country_schema.CountrySchema`
        validation with matching ``cca2``, ``region``, ``capital``, and
        ``population`` values.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            country (dict): A single entry from ``test_data/countries.json``
                containing ``name``, ``cca2``, and ``region`` keys.

        Returns:
            None
        """
        with allure.step(f"GET /name/{country['name']}"):
            response = api_client_fixture.get(f"/name/{country['name']}")

        with allure.step("Assert result count meets configured minimum"):
            results = response.json()
            assert len(results) >= api_client_fixture.min_results_count, (
                f"Expected at least {api_client_fixture.min_results_count} result(s), got {len(results)}"
            )

        with allure.step("Validate full schema of first result"):
            validated = CountrySchema.from_dict(results[0])
            assert validated.cca2 == country["cca2"]
            assert validated.region == country["region"]
            assert len(validated.capital) > 0
            assert validated.population > 0

    @allure.story("Country Lookup by Alpha Code — Schema Integrity")
    @pytest.mark.parametrize("country", _COUNTRIES, ids=[c["cca2"] for c in _COUNTRIES])
    def test_country_by_alpha_code(self, api_client_fixture: ApiClient, country: dict) -> None:
        """Verify schema integrity for alpha-code-based lookups.

        Issues a ``GET /alpha/{cca2}`` request and asserts that the response
        list meets the configured minimum length and that the first result
        passes full :class:`~validators.country_schema.CountrySchema`
        validation with non-empty ``currencies``, ``languages``, and ``name``
        fields.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            country (dict): A single entry from ``test_data/countries.json``
                containing ``name``, ``cca2``, and ``region`` keys.

        Returns:
            None
        """
        with allure.step(f"GET /alpha/{country['cca2']}"):
            response = api_client_fixture.get(f"/alpha/{country['cca2']}")

        with allure.step("Assert result count meets configured minimum"):
            results = response.json()
            assert len(results) >= api_client_fixture.min_results_count, (
                f"Expected at least {api_client_fixture.min_results_count} result(s), got {len(results)}"
            )

        with allure.step("Validate full schema of result"):
            validated = CountrySchema.from_dict(results[0])
            assert validated.cca2 == country["cca2"]
            assert len(validated.currencies) > 0
            assert len(validated.languages) > 0
            assert validated.name.common != ""
            assert validated.name.official != ""
