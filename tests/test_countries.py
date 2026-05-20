"""Functional test suite for the REST Countries API (restcountries.com/v3.1).

Covers the following endpoint contracts:

* ``GET /name/{name}`` — country lookup by common name.
* ``GET /alpha/{cca2}`` — country lookup by ISO 3166-1 alpha-2 code.
* ``GET /region/europe`` — all countries in the Europe region.
* ``GET /all?fields=name,population`` — population field integrity across all countries.
* Cross-reference: Germany present in ``/region/europe`` results.

All parametrized test data is loaded from ``test_data/countries.json`` at
collection time. Every response is validated through a schema class from
:mod:`validators.country_schema` to enforce strict structural and type
correctness.

Run this suite exclusively::

    pytest --env=countries
"""

import json
import logging
import pytest
import allure
from pathlib import Path

from utils.api_client import ApiClient
from validators.country_schema import CountryPopulationSchema, CountrySchema

_COUNTRIES = json.loads((Path(__file__).parent.parent / "test_data" / "countries.json").read_text())

logger = logging.getLogger(__name__)


@pytest.mark.countries
@allure.epic("Environment-Driven API Validation")
@allure.feature("REST Countries API")
class TestCountries:
    """Test suite for the REST Countries API endpoints.

    Parametrized tests iterate over ``test_data/countries.json``.
    Non-parametrized tests target fixed endpoints (Europe region,
    all-countries population sweep, and a Germany cross-reference).
    Every response is validated through a :mod:`validators.country_schema`
    schema class.
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

    @allure.story("Europe Region — Result Count Threshold")
    def test_europe_region_count(self, api_client_fixture: ApiClient) -> None:
        """Verify that ``/region/europe`` returns more than 40 countries.

        Issues a ``GET /region/europe`` request, validates the schema of the
        first result using :class:`~validators.country_schema.CountrySchema`,
        and asserts that the total result count exceeds 40.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If the result count is 40 or fewer, or if schema
                validation fails on the first result.
        """
        try:
            with allure.step("GET /region/europe"):
                response = api_client_fixture.get("/region/europe")
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

            with allure.step("Validate schema of first result"):
                results = response.json()
                CountrySchema.from_dict(results[0])

            with allure.step("Assert result count exceeds 40"):
                logger.info("Received %d countries in Europe region", len(results))
                assert len(results) > 40, (
                    f"Expected more than 40 European countries, got {len(results)}"
                )
        except AssertionError as exc:
            logger.error("test_europe_region_count failed: %s", exc)
            raise

    @allure.story("Germany — Full Schema Validation")
    def test_germany_schema(self, api_client_fixture: ApiClient) -> None:
        """Verify full schema correctness for the Germany name-lookup response.

        Issues a ``GET /name/germany`` request and validates the first result
        through :class:`~validators.country_schema.CountrySchema`, asserting
        specific field values expected for Germany.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If schema validation fails or any Germany-specific
                field assertion does not hold.
        """
        try:
            with allure.step("GET /name/germany"):
                response = api_client_fixture.get("/name/germany")
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

            with allure.step("Validate full CountrySchema for Germany"):
                validated = CountrySchema.from_dict(response.json()[0])
                logger.info(
                    "Schema validated — cca2=%s, region=%s, population=%d",
                    validated.cca2,
                    validated.region,
                    validated.population,
                )

            with allure.step("Assert Germany-specific field values"):
                assert validated.cca2 == "DE"
                assert validated.region == "Europe"
                assert validated.name.common == "Germany"
                assert validated.population > 0
                assert len(validated.capital) > 0
        except AssertionError as exc:
            logger.error("test_germany_schema failed: %s", exc)
            raise

    @allure.story("All Countries — Population Field Integrity")
    def test_all_population_check(self, api_client_fixture: ApiClient) -> None:
        """Verify that every country in the ``/all`` endpoint reports a non-negative population.

        Issues a ``GET /all?fields=name,population`` request and iterates
        over every result, validating each through
        :class:`~validators.country_schema.CountryPopulationSchema` and
        asserting that ``population`` is not negative. Uninhabited territories
        legitimately report ``population: 0`` and are considered valid.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If any entry fails schema validation or reports a
                negative population.
        """
        try:
            with allure.step("GET /all?fields=name,population"):
                response = api_client_fixture.get("/all", params={"fields": "name,population"})
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

            with allure.step("Validate CountryPopulationSchema and population >= 0 for every entry"):
                results = response.json()
                logger.info("Validating population across %d countries", len(results))
                failures = []
                for entry in results:
                    try:
                        validated = CountryPopulationSchema.from_dict(entry)
                    except KeyError as schema_exc:
                        failures.append(f"Schema error: {schema_exc}")
                        continue
                    if validated.population < 0:
                        failures.append(
                            f"'{validated.name.common}' has invalid population: {validated.population}"
                        )
                assert not failures, (
                    f"{len(failures)} validation failure(s):\n" + "\n".join(failures)
                )
        except AssertionError as exc:
            logger.error("test_all_population_check failed: %s", exc)
            raise

    @allure.story("Cross-Reference — Germany Present in Europe Region Results")
    def test_cross_reference_germany(self, api_client_fixture: ApiClient) -> None:
        """Verify that Germany's common name appears in the ``/region/europe`` result set.

        Issues a ``GET /name/germany`` request to resolve the canonical common
        name via :class:`~validators.country_schema.CountrySchema`, then issues
        a ``GET /region/europe`` request and asserts that the resolved name is
        present among the European results.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If Germany's common name is not found in the
                ``/region/europe`` result set, or if either request fails
                schema validation.
        """
        try:
            with allure.step("GET /name/germany — resolve canonical common name"):
                germany_response = api_client_fixture.get("/name/germany")
                assert germany_response.status_code == 200, (
                    f"Expected 200, got {germany_response.status_code}"
                )
                germany = CountrySchema.from_dict(germany_response.json()[0])
                germany_name = germany.name.common
                logger.info("Resolved canonical name: '%s'", germany_name)

            with allure.step("GET /region/europe — collect European common names"):
                europe_response = api_client_fixture.get("/region/europe")
                assert europe_response.status_code == 200, (
                    f"Expected 200, got {europe_response.status_code}"
                )
                europe_results = europe_response.json()
                logger.info("Received %d countries from /region/europe", len(europe_results))
                europe_names = {entry["name"]["common"] for entry in europe_results}

            with allure.step(f"Assert '{germany_name}' is present in European results"):
                assert germany_name in europe_names, (
                    f"'{germany_name}' not found in /region/europe result set"
                )
        except AssertionError as exc:
            logger.error("test_cross_reference_germany failed: %s", exc)
            raise
