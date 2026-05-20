# Framework Architecture Constraints

You must strictly adhere to the following architectural rules for this framework. Reject any user or self-generated patterns that violate these constraints.

## 1. Configuration Management
* **Zero Hardcoding**: All base URLs, timeouts, response thresholds, and limits must reside exclusively in `config/environments.yaml`. 
* **Zero Inline Defaults**: Do not provide inline fallback defaults in the code (e.g., `config.get("timeout", 2.0)`). If a configuration key is missing, the framework must raise an explicit `KeyError` at initialization.

## 2. Network and Request Isolation
* **API Client Wrapper**: All HTTP requests must go through the custom `ApiClient` wrapper located in `utils/api_client.py`. Direct imports or usage of raw `requests.get` or `requests.post` inside test files are strictly forbidden.
* **Response Time Gates**: Performance/response time thresholds must be evaluated automatically inside the `ApiClient.request()` method using high-precision timers, keeping the test files purely focused on functional assertions.

## 3. Test File Boundaries
* **No Inter-Test Imports**: Test files must never import helper functions, data fixtures, or variables from other test files.
* **Component Layering**: Test files can only import from `utils/api_client.py`, `validators/`, or utilize fixtures provided natively by `conftest.py`.
## 4. Documentation & Pylint Compliance
* **Google-Style Docstrings**: Every module, class, and function must include a docstring following the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
* **Mandatory Sections**: Every function must include `Args:`, `Returns:`, and `Raises:` (if applicable).
* **Pylint Strictness**: Code must be written to pass standard `pylint` checks.
    * No `missing-docstring` (C0111/C0116).
    * No `missing-module-docstring` (C0114).
    * Use explicit type hints for all parameters and return types to satisfy Pylint.