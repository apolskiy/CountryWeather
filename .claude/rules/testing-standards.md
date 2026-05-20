# Project Testing Conventions

Every test generated for this test suite must pass the following quality gates:

## 1. Test Data Sourcing
* **Externalized Datasets**: Never inline test data arrays or dictionaries inside test methods. 
* **JSON Sourcing**: Complex parameters (such as coordinate matrices, cities, or user profiles) must be parsed from `test_data/` files (e.g., `test_data/cities.json`) using pytest parameterization hooks.

## 2. Schema Enforcement
* **Mandatory Validation**: Every endpoint verification test must execute a full structural validation against a predefined type/schema class. 
* **No Shallow Presence Checks**: Verifying a key exists via `assert "name" in response` is insufficient. Every required field must be validated for type correctness and structural consistency.

## 3. Reporting Hooks
* **Allure Metadata**: Every test function must be explicitly decorated with an environment marker (`@pytest.mark.countries` or `@pytest.mark.weather`) and an Allure step description to ensure reports are cleanly segmented.