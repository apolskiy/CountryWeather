"""Extended test suite for the REST Countries API (api.restcountries.com v5).

Provides standalone coverage complementary to ``tests/test_countries.py``,
targeting the following endpoint contracts:

* ``GET /region/europe`` — regional result-count threshold (paginated).
* ``GET /names.common/germany`` — full schema enforcement via
  :class:`~validators.country_schema.CountrySchema`.
* ``GET /`` (root) — population field integrity sweep (paginated, field
  filtered).
* Cross-reference: Germany's region is resolved dynamically, then verified
  against the corresponding ``/region/{region}`` result set.
* Negative: a non-existent country name must yield an empty result set
  (v5 returns HTTP 200 with ``data.objects == []`` rather than a 404).

Network interactions are performed exclusively through the ``api_client_fixture``
provided by ``conftest.py``; the v5 ``data.objects`` envelope is unwrapped by
:meth:`utils.api_client.ApiClient.get_objects`. Schema enforcement is delegated
to classes in :mod:`validators.country_schema`.

Run this suite exclusively::

    pytest tests/test_country_api.py --env=countries
"""

import logging

import allure
import pytest

from utils.api_client import ApiClient
from validators.country_schema import CountryPopulationSchema, CountrySchema

logger = logging.getLogger(__name__)


@pytest.mark.countries
@allure.epic("Environment-Driven API Validation")
@allure.feature("REST Countries API — Extended Coverage")
class TestCountryApi:
    """Extended test suite for the REST Countries v5 API.

    Each test exercises a distinct contract: regional count thresholds,
    full schema enforcement, field-level integrity sweeps, dynamic
    cross-referencing, and negative empty-result handling. All requests
    are routed through ``api_client_fixture``.
    """

    @allure.story("Region — Europe Result Count Threshold")
    def test_europe_region_count(self, api_client_fixture: ApiClient) -> None:
        """Verify that ``/region/europe`` returns more than 40 countries.

        Sends a paginated ``GET /region/europe`` request and asserts the
        unwrapped object list contains more than 40 entries, confirming that
        the regional endpoint returns a meaningful dataset rather than a
        truncated or empty result.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If the result count is 40 or fewer.
        """
        try:
            with allure.step("GET /region/europe (paginated)"):
                results = api_client_fixture.get_objects("/region/europe", paginate=True)

            with allure.step("Assert result count exceeds 40"):
                logger.info("/region/europe returned %d countries", len(results))
                assert len(results) > 40, (
                    f"Expected more than 40 European countries, got {len(results)}"
                )
        except AssertionError as exc:
            logger.error("test_europe_region_count failed: %s", exc)
            raise

    @allure.story("Schema — Germany Full Structural Validation")
    def test_germany_schema_validation(self, api_client_fixture: ApiClient) -> None:
        """Verify full schema correctness for a ``/names.common/germany`` response.

        Sends a ``GET /names.common/germany`` request and validates the first
        result through :class:`~validators.country_schema.CountrySchema`,
        confirming that ``name``, ``capital``, ``population``, ``currencies``,
        and ``languages`` are present, correctly typed, and non-empty.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If schema validation fails or any required field
                is absent, incorrectly typed, or empty.
        """
        try:
            with allure.step("GET /names.common/germany"):
                results = api_client_fixture.get_objects("/names.common/germany")

            with allure.step("Validate CountrySchema — name, capital, population, currencies, languages"):
                validated = CountrySchema.from_dict(results[0])
                logger.info(
                    "Schema validated — name='%s', capital=%s, population=%d",
                    validated.name.common,
                    validated.capital,
                    validated.population,
                )
                assert validated.name.common != "", (
                    "Expected non-empty 'name.common' for Germany"
                )
                assert validated.name.official != "", (
                    "Expected non-empty 'name.official' for Germany"
                )
                assert len(validated.capital) > 0, (
                    "Expected at least one entry in 'capital' for Germany"
                )
                assert validated.population > 0, (
                    f"Expected positive population for Germany, got {validated.population}"
                )
                assert len(validated.currencies) > 0, (
                    "Expected at least one currency entry for Germany"
                )
                assert len(validated.languages) > 0, (
                    "Expected at least one language entry for Germany"
                )
        except AssertionError as exc:
            logger.error("test_germany_schema_validation failed: %s", exc)
            raise

    @allure.story("Field Integrity — All Countries Population Sweep")
    def test_all_countries_population_integrity(self, api_client_fixture: ApiClient) -> None:
        """Verify population is a non-negative integer for every country.

        Sends a paginated ``GET /`` request filtered to
        ``response_fields=names.common,population`` and iterates over every
        result, validating each through
        :class:`~validators.country_schema.CountryPopulationSchema` and
        asserting that ``population`` is not negative. Uninhabited territories
        legitimately report ``population: 0`` in the API and are treated as
        valid; only negative values are flagged.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If any entry fails schema validation or reports
                a negative population.
        """
        try:
            with allure.step("GET / (paginated, response_fields=names.common,population)"):
                results = api_client_fixture.get_objects(
                    "",
                    params={"response_fields": "names.common,population"},
                    paginate=True,
                )

            with allure.step("Assert population >= 0 for every country entry"):
                logger.info("Sweeping population field across %d entries", len(results))
                failures = []
                for entry in results:
                    try:
                        validated = CountryPopulationSchema.from_dict(entry)
                    except KeyError as schema_exc:
                        failures.append(f"Schema error on entry: {schema_exc}")
                        continue
                    if validated.population < 0:
                        failures.append(
                            f"'{validated.name_common}' has invalid population: {validated.population}"
                        )
                assert not failures, (
                    f"{len(failures)} population integrity failure(s):\n" + "\n".join(failures)
                )
                logger.info("All %d entries passed population integrity check", len(results))
        except AssertionError as exc:
            logger.error("test_all_countries_population_integrity failed: %s", exc)
            raise

    @allure.story("Cross-Reference — Germany Present in Its Own Region")
    def test_germany_cross_reference_region(self, api_client_fixture: ApiClient) -> None:
        """Verify Germany appears in the results for its own dynamically resolved region.

        Sends a ``GET /names.common/germany`` request and extracts the
        ``region`` and ``name.common`` fields via
        :class:`~validators.country_schema.CountrySchema`. Then sends a
        paginated ``GET /region/{region}`` request and asserts that Germany's
        common name is present in the returned country list.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If Germany's common name is absent from the
                ``/region/{region}`` result set, or if either request fails
                schema validation.
        """
        try:
            with allure.step("GET /names.common/germany — resolve common name and region"):
                germany_results = api_client_fixture.get_objects("/names.common/germany")
                germany = CountrySchema.from_dict(germany_results[0])
                region = germany.region
                common_name = germany.name.common
                logger.info("Resolved country='%s', region='%s'", common_name, region)

            with allure.step(f"GET /region/{region} — fetch all countries in Germany's region (paginated)"):
                region_results = api_client_fixture.get_objects(f"/region/{region}", paginate=True)
                logger.info("/region/%s returned %d countries", region, len(region_results))

            with allure.step(f"Assert '{common_name}' is present in /region/{region} results"):
                region_names = {entry["names"]["common"] for entry in region_results}
                assert common_name in region_names, (
                    f"'{common_name}' not found among {len(region_names)} countries "
                    f"returned by /region/{region}"
                )
        except AssertionError as exc:
            logger.error("test_germany_cross_reference_region failed: %s", exc)
            raise

    @allure.story("Negative — Non-existent Country Name Returns an Empty Result Set")
    def test_nonexistent_country_returns_empty(self, api_client_fixture: ApiClient) -> None:
        """Verify that a lookup for a non-existent country name yields no results.

        Sends a ``GET /names.common/{invalid}`` request. The v5 API responds
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
