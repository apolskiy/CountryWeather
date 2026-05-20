"""Extended test suite for the REST Countries API (restcountries.com/v3.1).

Provides standalone coverage complementary to ``tests/test_countries.py``,
targeting the following endpoint contracts:

* ``GET /region/europe`` — regional result-count threshold.
* ``GET /name/germany`` — full schema enforcement via
  :class:`~validators.country_schema.CountrySchema`.
* ``GET /all?fields=name,population`` — population field integrity sweep.
* Cross-reference: Germany's region is resolved dynamically, then verified
  against the corresponding ``/region/{region}`` result set.
* Negative: a non-existent country name must yield HTTP 404.

Network interactions are performed exclusively through the ``api_client_fixture``
provided by ``conftest.py``. Schema enforcement is delegated to classes in
:mod:`validators.country_schema`.

Run this suite exclusively::

    pytest tests/test_country_api.py --env=countries
"""

import logging

import allure
import pytest
import requests

from utils.api_client import ApiClient
from validators.country_schema import CountryPopulationSchema, CountrySchema

logger = logging.getLogger(__name__)


@pytest.mark.countries
@allure.epic("Environment-Driven API Validation")
@allure.feature("REST Countries API — Extended Coverage")
class TestCountryApi:
    """Extended test suite for the REST Countries API.

    Each test exercises a distinct contract: regional count thresholds,
    full schema enforcement, field-level integrity sweeps, dynamic
    cross-referencing, and negative HTTP-error handling. All requests
    are routed through ``api_client_fixture``.
    """

    @allure.story("Region — Europe Result Count Threshold")
    def test_europe_region_count(self, api_client_fixture: ApiClient) -> None:
        """Verify that ``/region/europe`` returns more than 40 countries.

        Sends a ``GET /region/europe`` request and asserts the response list
        contains more than 40 entries, confirming that the regional endpoint
        returns a meaningful dataset rather than a truncated or empty result.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If the result count is 40 or fewer.
        """
        try:
            with allure.step("GET /region/europe"):
                response = api_client_fixture.get("/region/europe")
                assert response.status_code == 200, (
                    f"Expected HTTP 200 from /region/europe, got {response.status_code}"
                )

            with allure.step("Assert result count exceeds 40"):
                results = response.json()
                logger.info("/region/europe returned %d countries", len(results))
                assert len(results) > 40, (
                    f"Expected more than 40 European countries, got {len(results)}"
                )
        except AssertionError as exc:
            logger.error("test_europe_region_count failed: %s", exc)
            raise

    @allure.story("Schema — Germany Full Structural Validation")
    def test_germany_schema_validation(self, api_client_fixture: ApiClient) -> None:
        """Verify full schema correctness for a ``/name/germany`` response.

        Sends a ``GET /name/germany`` request and validates the first result
        through :class:`~validators.country_schema.CountrySchema`, confirming
        that ``name``, ``capital``, ``population``, ``currencies``, and
        ``languages`` are present, correctly typed, and non-empty.

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
            with allure.step("GET /name/germany"):
                response = api_client_fixture.get("/name/germany")
                assert response.status_code == 200, (
                    f"Expected HTTP 200 from /name/germany, got {response.status_code}"
                )

            with allure.step("Validate CountrySchema — name, capital, population, currencies, languages"):
                validated = CountrySchema.from_dict(response.json()[0])
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
        """Verify population is a non-negative integer for every ``/all`` entry.

        Sends a ``GET /all?fields=name,population`` request and iterates over
        every result, validating each through
        :class:`~validators.country_schema.CountryPopulationSchema` and
        asserting that ``population`` is not negative. Five uninhabited
        territories (e.g. Bouvet Island) legitimately report ``population: 0``
        in the API and are treated as valid; only negative values are flagged.

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
            with allure.step("GET /all?fields=name,population"):
                response = api_client_fixture.get("/all", params={"fields": "name,population"})
                assert response.status_code == 200, (
                    f"Expected HTTP 200 from /all, got {response.status_code}"
                )

            with allure.step("Assert population >= 0 for every country entry"):
                results = response.json()
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
                            f"'{validated.name.common}' has invalid population: {validated.population}"
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

        Sends a ``GET /name/germany`` request and extracts the ``region`` and
        ``name.common`` fields via :class:`~validators.country_schema.CountrySchema`.
        Then sends a ``GET /region/{region}`` request and asserts that Germany's
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
            with allure.step("GET /name/germany — resolve common name and region"):
                germany_response = api_client_fixture.get("/name/germany")
                assert germany_response.status_code == 200, (
                    f"Expected HTTP 200 from /name/germany, got {germany_response.status_code}"
                )
                germany = CountrySchema.from_dict(germany_response.json()[0])
                region = germany.region
                common_name = germany.name.common
                logger.info("Resolved country='%s', region='%s'", common_name, region)

            with allure.step(f"GET /region/{region} — fetch all countries in Germany's region"):
                region_response = api_client_fixture.get(f"/region/{region}")
                assert region_response.status_code == 200, (
                    f"Expected HTTP 200 from /region/{region}, got {region_response.status_code}"
                )
                region_results = region_response.json()
                logger.info("/region/%s returned %d countries", region, len(region_results))

            with allure.step(f"Assert '{common_name}' is present in /region/{region} results"):
                region_names = {entry["name"]["common"] for entry in region_results}
                assert common_name in region_names, (
                    f"'{common_name}' not found among {len(region_names)} countries "
                    f"returned by /region/{region}"
                )
        except AssertionError as exc:
            logger.error("test_germany_cross_reference_region failed: %s", exc)
            raise

    @allure.story("Negative — Non-existent Country Name Returns HTTP 404")
    def test_nonexistent_country_returns_404(self, api_client_fixture: ApiClient) -> None:
        """Verify that a lookup for a non-existent country name yields HTTP 404.

        Sends a ``GET /name/zzz_nonexistent_country_xyz`` request. Because
        :class:`~utils.api_client.ApiClient` calls
        :meth:`~requests.Response.raise_for_status` internally, a 4xx response
        surfaces as :exc:`requests.HTTPError`. The test asserts that the
        embedded status code is exactly 404.

        Args:
            api_client_fixture (ApiClient): Environment-scoped HTTP client
                provided by ``conftest.py``.

        Returns:
            None

        Raises:
            AssertionError: If the raised :exc:`requests.HTTPError` does not
                carry an HTTP 404 status code.
        """
        invalid_name = "zzz_nonexistent_country_xyz"

        with allure.step(f"GET /name/{invalid_name} — expect requests.HTTPError"):
            with pytest.raises(requests.HTTPError) as exc_info:
                api_client_fixture.get(f"/name/{invalid_name}")

        with allure.step("Assert embedded HTTP status code is 404"):
            status_code = exc_info.value.response.status_code
            logger.info(
                "Non-existent country '%s' correctly returned HTTP %d",
                invalid_name,
                status_code,
            )
            assert status_code == 404, (
                f"Expected HTTP 404 for non-existent country '{invalid_name}', got {status_code}"
            )
