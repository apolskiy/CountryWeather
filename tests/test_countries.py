"""Functional test suite for the REST Countries API (api.restcountries.com v5).

Covers the following endpoint contracts:

* ``GET /names.common/{name}`` - country lookup by common name.
* ``GET /codes.alpha_2/{code}`` - country lookup by ISO 3166-1 alpha-2 code.
* ``GET /region/{region}`` - all countries in a region.
* ``GET /`` (root) - all-countries population field integrity sweep
  (paginated; ``response_fields`` filtered to ``names.common,population``).
* ``GET /names.common/{name}`` + ``GET /region/{region}`` - cross-reference
  that each entity appears in its own region's result set.

All entity-driven tests declare an ``entity`` parameter and are parametrized by
the ``pytest_generate_tests`` hook in :mod:`conftest` over every record in
``test_data/master_entities.json`` (the single source of truth). Responses are
read through :meth:`utils.api_client.ApiClient.get_objects`, which unwraps the
v5 ``data.objects`` envelope and paginates as needed. Every country object is
validated through a schema class from :mod:`validators.country_schema`.

Run this suite exclusively::

    pytest --env=countries
"""

import logging

import allure
import pytest

from utils.api_client import ApiClient
from validators.country_schema import CountryPopulationSchema, CountrySchema

logger = logging.getLogger(__name__)


@pytest.mark.countries
@allure.epic("Environment-Driven API Validation")
@allure.feature("REST Countries API")
class TestCountries:
    """Test suite for the REST Countries v5 API endpoints.

    Entity-driven tests declare an ``entity`` parameter and iterate over
    ``test_data/master_entities.json`` via the ``pytest_generate_tests`` hook
    in ``conftest.py``. Region-wide tests target fixed endpoints (Europe region
    and the all-countries population sweep). Every response is validated through
    a :mod:`validators.country_schema` schema class.
    """

    @allure.story("Country Lookup by Name - Schema and Count")
    def test_country_by_name(self, api_client_fixture: ApiClient, entity: dict) -> None:
        """Verify schema correctness and result count for name-based lookups.

        Issues a ``GET /names.common/{name}`` request and asserts that the
        unwrapped object list meets the configured minimum length and that the
        first result passes full
        :class:`~validators.country_schema.CountrySchema` validation with
        matching ``cca2``, ``region``, ``capital``, and ``population`` values.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            entity (dict): A single record from
                ``test_data/master_entities.json`` containing ``name``,
                ``cca2``, and ``region`` keys (among others).

        Returns:
            None
        """
        with allure.step(f"GET /names.common/{entity['name']}"):
            results = api_client_fixture.get_objects(f"/names.common/{entity['name']}")

        with allure.step("Assert result count meets configured minimum"):
            assert len(results) >= api_client_fixture.min_results_count, (
                f"Expected at least {api_client_fixture.min_results_count} result(s), got {len(results)}"
            )

        with allure.step("Validate full schema of first result"):
            validated = CountrySchema.from_dict(results[0])
            assert validated.cca2 == entity["cca2"]
            assert validated.region == entity["region"]
            assert len(validated.capital) > 0
            assert validated.population > 0

    @allure.story("Country Lookup by Alpha Code - Schema Integrity")
    def test_country_by_alpha_code(self, api_client_fixture: ApiClient, entity: dict) -> None:
        """Verify schema integrity for alpha-code-based lookups.

        Issues a ``GET /codes.alpha_2/{code}`` request and asserts that the
        unwrapped object list meets the configured minimum length and that the
        first result passes full
        :class:`~validators.country_schema.CountrySchema` validation with
        non-empty ``currencies``, ``languages``, and ``name`` fields.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            entity (dict): A single record from
                ``test_data/master_entities.json`` containing ``name``,
                ``cca2``, and ``region`` keys (among others).

        Returns:
            None
        """
        with allure.step(f"GET /codes.alpha_2/{entity['cca2']}"):
            results = api_client_fixture.get_objects(f"/codes.alpha_2/{entity['cca2']}")

        with allure.step("Assert result count meets configured minimum"):
            assert len(results) >= api_client_fixture.min_results_count, (
                f"Expected at least {api_client_fixture.min_results_count} result(s), got {len(results)}"
            )

        with allure.step("Validate full schema of result"):
            validated = CountrySchema.from_dict(results[0])
            assert validated.cca2 == entity["cca2"]
            assert len(validated.currencies) > 0
            assert len(validated.languages) > 0
            assert validated.name.common != ""
            assert validated.name.official != ""

    @allure.story("Country - Full Schema Validation")
    def test_country_full_schema(self, api_client_fixture: ApiClient, entity: dict) -> None:
        """Verify full schema correctness for an entity's name-lookup response.

        Issues a ``GET /names.common/{name}`` request and validates the first
        result through :class:`~validators.country_schema.CountrySchema`,
        asserting that the resolved ``cca2`` and ``region`` match the dataset
        record and that the common/official names, capital, and population are
        populated.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            entity (dict): A single record from
                ``test_data/master_entities.json`` containing ``name``,
                ``cca2``, and ``region`` keys (among others).

        Returns:
            None

        Raises:
            AssertionError: If schema validation fails or any field assertion
                does not hold.
        """
        try:
            with allure.step(f"GET /names.common/{entity['name']}"):
                results = api_client_fixture.get_objects(f"/names.common/{entity['name']}")

            with allure.step(f"Validate full CountrySchema for {entity['name']}"):
                validated = CountrySchema.from_dict(results[0])
                logger.info(
                    "Schema validated - cca2=%s, region=%s, population=%d",
                    validated.cca2,
                    validated.region,
                    validated.population,
                )

            with allure.step("Assert resolved fields match the dataset record"):
                assert validated.cca2 == entity["cca2"]
                assert validated.region == entity["region"]
                assert validated.name.common != ""
                assert validated.name.official != ""
                assert validated.population > 0
                assert len(validated.capital) > 0
        except AssertionError as exc:
            logger.error("test_country_full_schema failed for %s: %s", entity["name"], exc)
            raise

    @allure.story("Europe Region - Result Count Threshold")
    def test_europe_region_count(self, api_client_fixture: ApiClient) -> None:
        """Verify that ``/region/europe`` returns more than 40 countries.

        Issues a paginated ``GET /region/europe`` request, validates the schema
        of the first result using
        :class:`~validators.country_schema.CountrySchema`, and asserts that the
        total result count exceeds 40.

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
            with allure.step("GET /region/europe (paginated)"):
                results = api_client_fixture.get_objects("/region/europe", paginate=True)

            with allure.step("Validate schema of first result"):
                CountrySchema.from_dict(results[0])

            with allure.step("Assert result count exceeds 40"):
                logger.info("Received %d countries in Europe region", len(results))
                assert len(results) > 40, (
                    f"Expected more than 40 European countries, got {len(results)}"
                )
        except AssertionError as exc:
            logger.error("test_europe_region_count failed: %s", exc)
            raise

    @allure.story("All Countries - Population Field Integrity")
    def test_all_population_check(self, api_client_fixture: ApiClient) -> None:
        """Verify that every country reports a non-negative population.

        Issues a paginated ``GET /`` request filtered to
        ``response_fields=names.common,population`` and iterates over every
        result, validating each through
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
            with allure.step("GET / (paginated, response_fields=names.common,population)"):
                results = api_client_fixture.get_objects(
                    "",
                    params={"response_fields": "names.common,population"},
                    paginate=True,
                )

            with allure.step("Validate CountryPopulationSchema and population >= 0 for every entry"):
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
                            f"'{validated.name_common}' has invalid population: {validated.population}"
                        )
                assert not failures, (
                    f"{len(failures)} validation failure(s):\n" + "\n".join(failures)
                )
        except AssertionError as exc:
            logger.error("test_all_population_check failed: %s", exc)
            raise

    @allure.story("Cross-Reference - Country Present in Its Own Region Results")
    def test_country_present_in_region(self, api_client_fixture: ApiClient, entity: dict) -> None:
        """Verify that an entity's common name appears in its own region's result set.

        Issues a ``GET /names.common/{name}`` request to resolve the canonical
        common name and region via
        :class:`~validators.country_schema.CountrySchema`, then issues a
        paginated ``GET /region/{region}`` request and asserts that the
        resolved name is present among that region's results.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.
            entity (dict): A single record from
                ``test_data/master_entities.json`` containing ``name`` and
                ``region`` keys (among others).

        Returns:
            None

        Raises:
            AssertionError: If the entity's common name is not found in its
                region's result set, or if either request fails schema
                validation.
        """
        try:
            with allure.step(f"GET /names.common/{entity['name']} - resolve canonical name and region"):
                name_results = api_client_fixture.get_objects(f"/names.common/{entity['name']}")
                validated = CountrySchema.from_dict(name_results[0])
                common_name = validated.name.common
                region = validated.region
                assert region == entity["region"], (
                    f"Resolved region '{region}' does not match dataset '{entity['region']}'"
                )
                logger.info("Resolved canonical name='%s', region='%s'", common_name, region)

            with allure.step(f"GET /region/{region} - collect common names (paginated)"):
                region_results = api_client_fixture.get_objects(f"/region/{region}", paginate=True)
                logger.info("Received %d countries from /region/%s", len(region_results), region)
                region_names = {item["names"]["common"] for item in region_results}

            with allure.step(f"Assert '{common_name}' is present in /region/{region} results"):
                assert common_name in region_names, (
                    f"'{common_name}' not found in /region/{region} result set"
                )
        except AssertionError as exc:
            logger.error("test_country_present_in_region failed for %s: %s", entity["name"], exc)
            raise

    @allure.story("Negative - Non-existent Country Name Returns an Empty Result Set")
    def test_nonexistent_country_returns_empty(self, api_client_fixture: ApiClient) -> None:
        """Verify that a lookup for a non-existent country name yields no results.

        Issues a ``GET /names.common/{invalid}`` request. The v5 API responds
        with HTTP 200 and an empty ``data.objects`` array for unknown names
        (rather than a 404), so the test asserts that the unwrapped object
        list is empty.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If the lookup returns any results for a name that
                does not correspond to a real country.
        """
        invalid_name = "zzz_nonexistent_country_xyz"

        try:
            with allure.step(f"GET /names.common/{invalid_name}"):
                results = api_client_fixture.get_objects(f"/names.common/{invalid_name}")

            with allure.step("Assert the result set is empty"):
                logger.info(
                    "Non-existent country '%s' correctly returned %d results",
                    invalid_name,
                    len(results),
                )
                assert results == [], (
                    f"Expected no results for non-existent country '{invalid_name}', got {len(results)}"
                )
        except AssertionError as exc:
            logger.error("test_nonexistent_country_returns_empty failed: %s", exc)
            raise
