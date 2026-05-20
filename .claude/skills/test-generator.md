# Skill: Test Generator for CountryWeather Framework

# Skill: Test Generator for PANW-QA Framework

## Context
Use this skill when asked to write a new pytest file. The generated file must follow `framework-rules.md`, maintain Pylint compliance (Google-style docstrings, type hints), use the `ApiClient` pattern for requests, utilize `allure` decorators, implement logging on assertion failure, and provide both positive and negative test cases.

## Inputs Required
* Endpoint URL / Path
* HTTP Method
* Targeted Environment Marker (`countries` or `weather`)
* Validation Logic / Schema Class

## Execution Template
Generate output conforming strictly to this layout:

```python
"""
Module-level docstring: Test suite for [Component Name] functionality.
"""
import logging
import pytest
import allure
from utils.api_client import ApiClient
from validators.YOUR_VALIDATOR import YourValidator

logger = logging.getLogger(__name__)

@pytest.mark.MARKER_NAME
@allure.epic("Environment-Driven API Validation")
@allure.feature("[Feature Name]")
class TestYourComponent:
    """
    Test suite for [Feature Name] validation.
    """

    @allure.story("Positive Functional Flow")
    def test_positive_flow(self, api_client: ApiClient) -> None:
        """
        Validates the positive functional flow for the endpoint.

        Args:
            api_client: The injected ApiClient instance.

        Returns:
            None

        Raises:
            AssertionError: If validation or status code checks fail.
        """
        try:
            with allure.step("Execute API Request"):
                response = api_client.get("[ENDPOINT_URL]")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            with allure.step("Validate Response Structure"):
                validated_data = YourValidator.from_dict(response.json())
                assert validated_data is not None
        except AssertionError as e:
            logger.error(f"Positive test failed for [ENDPOINT_URL]: {e}")
            raise

    @allure.story("Negative Validation")
    def test_negative_invalid_input(self, api_client: ApiClient) -> None:
        """
        Validates error handling for edge cases.

        Args:
            api_client: The injected ApiClient instance.

        Returns:
            None
        """
        try:
            # Implement negative scenario (e.g., invalid path or param)
            response = api_client.get("/invalid-path")
            assert response.status_code in [400, 404], "Should return client error"
        except AssertionError as e:
            logger.error(f"Negative test failed: {e}")
            raise