# Project Code Style

Conventions every generated or edited Python file in this repository must follow.
These are the mechanical rules - naming, typing, layout. Architectural constraints
live in `framework-rules.md`, and test-authoring rules in `testing-standards.md`.

## 1. Naming
* **Module-Level Constants**: Private module constants are `_UPPER_SNAKE_CASE` with a leading underscore (`_CONFIG_PATH`, `_SUPPORTED_ENVS`, `_DEFAULT_BASE_URL`). Reserve names without the underscore for values another module is expected to import.
* **Encapsulated State**: Instance attributes are private (`self._base_url`, `self._max_retries`). Expose a value to test files only through an explicit `@property`, as `ApiClient.min_results_count` does - never by promoting the attribute to public.
* **Private Helpers**: Methods and functions used only within their own module take a leading underscore (`_throttle`, `_retry_delay`, `_collect_env_metadata`).
* **Test Naming**: Test classes are `TestX`; test functions are `test_snake_case`; fixtures end in `_fixture` (`api_client_fixture`).

## 2. Type Annotations
* **Annotate Everything**: Every parameter and return type carries a hint, including `-> None` on procedures and `**kwargs: Any` on pass-through signatures.
* **Built-In Generics**: Use `list[dict]`, `dict[str, Any]`, `frozenset[int]` - not `typing.List` / `typing.Dict`. The suite runs on Python 3.14. `validators/country_schema.py` and `validators/weather_schema.py` still import `Dict` and `List` from `typing`; that is legacy, not the pattern to copy.
* **Optional Is Explicit**: A value that may be absent is annotated `Optional[X]` rather than left unannotated or given a bare default.
* **Annotate Declarations**: Local collections built up across a loop declare their type at the point of creation (`objects: list[dict] = []`).

## 3. Docstring Formatting
Google style and the mandatory `Args:` / `Returns:` / `Raises:` sections are required by `framework-rules.md`. This section fixes *how* they are written:

* **Types In Parentheses**: Each `Args:` entry names its type - `env_config (dict): A single environment block...`. `Returns:` leads with the type - `requests.Response: The HTTP response object...`.
* **Returns Is Never Omitted**: A function returning nothing still documents `Returns:` with `None`.
* **Sphinx Cross-References In Prose**: Refer to code with the `:class:`, `:meth:`, `:func:`, `:exc:` and `:mod:` roles, each wrapping its target in single backticks - as `utils/api_client.py` does when it points at `ApiClient`, `request`, and `KeyError`. Literals - config keys, paths, header names, HTTP methods - go in double backticks instead.
* **Module Docstrings State Contracts**: A module docstring explains what the module guarantees and how it is meant to be used, not merely what it contains. Test modules list the endpoint contracts they cover and the command that runs them.

## 4. Imports
* **Three Groups**: Standard library, third-party, then first-party (`utils`, `validators`), each separated by one blank line.
* **Absolute Only**: Import as `from utils.api_client import ApiClient`. No relative imports, no wildcard imports.
* **Module-Level Logger**: A module that logs declares `logger = logging.getLogger(__name__)` immediately after its imports.

## 5. Layout
* **Line Length**: 100 characters, the limit set in `.pylintrc`. Wrap long signatures one parameter per line with a trailing comma; wrap long assertion messages into a parenthesised f-string.
* **Double Quotes**: Strings use double quotes throughout. Interpolate with f-strings, never `%` or `.format()`.
* **Keyword-Only Flags**: Boolean options are keyword-only, declared after a bare `*` in the signature (`def get_objects(self, path, params=None, *, paginate=False)`), so no call site passes a bare `True`.

## 6. Data and Failure Handling
* **Dataclass Schemas**: Validators are `@dataclass` classes whose fields are constructed only through a `from_dict` classmethod returning the class's own type.
* **Check Before Constructing**: `from_dict` verifies every required key is present before building the instance, raising `KeyError` with the field named in the message: `f"Missing mandatory schema field: '{field}'"`.
* **Cast Explicitly**: Parsed values are coerced at construction - `str(...)`, `int(...)`, `dict(...)` - so a wrong upstream type fails at the boundary rather than inside an assertion.
* **Chain Re-Raises**: Re-raising in an `except` block uses `raise ... from exc`, preserving the original cause.
* **Catch Narrowly**: Catch specific exception classes (`requests.ConnectionError`, `requests.Timeout`, `ValueError`). No bare `except:`, and no `except Exception` used to steer control flow.

## 7. Comments
* **Explain Why, Not What**: Comments are rare and justify a decision the code cannot state itself - why the throttle timestamp lives on the class rather than the instance, why backoff time is excluded from the response-time measurement. Never restate the line below.
