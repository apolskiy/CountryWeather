# CLAUDE_LOG.md

## 1. Parallel Agent Workstreams
To optimize framework scaffolding, two independent workstreams were executed simultaneously via parallel agent instances to decouple the implementation of the two target APIs.

*   **Workstream A**: REST Countries API implementation.
*   **Workstream B**: Open-Meteo Weather API implementation.
*   **Net Engineering Savings**: ~33 minutes of boilerplate development time.

---

## 2. Architectural Decision Validation: Configuration Injection
**Context**: Injecting environment-specific configuration without violating test isolation.

**The Decision**: Rejected direct YAML parsing in the `ApiClient`. Implemented a dependency injection pattern where `conftest.py` orchestrates configuration injection.
*   **Rationale**: Decouples the API client from the file system, enabling unit testing of the client layer in isolation.
*   **Result**: The client is now data-agnostic and enforces strict contract validation.

---

## 3. Infrastructure & Environment Management
**Context**: Transitioned from internal VM runners to `ubuntu-latest` (GitHub Cloud).
*   **Performance**: Standardized on `MAX_RESPONSE_TIME` thresholds. Refused to artificially inflate timeouts, choosing instead to enforce accurate performance SLAs.
*   **Compatibility**: Enforced `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` to eliminate deprecation warnings.
*   **Artifact Robustness**: Refactored artifact collection (`if: always()`) to ensure JUnit/Allure reports are persisted even during test failures.

---

## 4. API Contract Migration: REST Countries v3.1 to v5
**The Problem**: The upstream provider hard-deprecated all pre-v5 versions (v1–v4.1 now return an error envelope), introducing a mandatory API-key requirement and a new response shape.

**The Solution**: 
1. **Authentication Injection**: `ApiClient` attaches `RESTCOUNTRIES_API_KEY` as a `Bearer` token, read from the process environment (never logged or hardcoded) and supplied in CI via GitHub Actions Secrets.
2. **Envelope & Pagination**: Added `ApiClient.get_objects` to unwrap the v5 `data.objects` envelope and transparently paginate list endpoints (the API caps page size at 100).
3. **Endpoint & Schema Remap**: Migrated paths (`/names.common`, `/codes.alpha_2`, `/region`) and rewrote the dataclass validators for the v5 field model (`names.*`, `codes.alpha_2`, `capitals`, list-based `currencies`/`languages`, `flag`).
4. **Negative Contract**: v5 returns HTTP 200 with an empty result set (not a 404) for unknown names; the negative test asserts emptiness accordingly.

---

## 5. Refactoring: Data Normalization & Data-Driven Testing
**The Problem**: Redundant JSON structures (`cities.json`, `coordinates.json`, `countries.json`) created maintenance overhead and synchronization drift. Hardcoded values in tests bypassed the framework's data-driven capabilities.

**The Solution**: Consolidated all entity data into a single `test_data/master_entities.json`. Migrated the test suite to use `pytest.mark.parametrize` to consume this "Single Source of Truth."

**Impact**: 
*   Reduced data surface area by 60%.
*   Adding new test entities now requires zero code changes; coverage expands automatically.
*   Enforced data consistency between Countries and Weather API suites.

---

## 6. LLM Error Analysis
**Claude's Suggestion**: Singleton pattern for `ApiClient`.
**Resolution**: Overruled. Global state creates cross-thread pollution in `pytest-xdist`. Implemented a dynamic fixture pattern in `conftest.py` using `pytest_runtest_setup(item)` to ensure thread safety.

---

## 7. How Rules Changed Claude's Output
| Category | Default Output | Governed Output (With Rules) |
| :--- | :--- | :--- |
| **Documentation** | No docstrings. | Google-style docstrings. |
| **Style** | Standard formatting. | Strict type hinting & Pylint compliance. |
| **Complexity** | Inline logic. | Separation of Schema and Request logic. |

---

## 8. Extensibility Audit
**Action**: Implemented a shared `test_data` utility layer, ensuring cross-reference tests remain DRY (Don't Repeat Yourself) and maintainable.

---

## 9. Network Resilience Hardening
**The Problem**: A CI run hung for ~18 minutes on a single test. Root cause: the `ApiClient` issued `requests` calls with no timeout (`read timeout=None`), so a transient TLS-handshake stall to Open-Meteo blocked until the kernel killed the socket (`Errno 110`) — turning a momentary network blip into a red, multi-minute build.

**The Solution**:
1. **Hard Timeout**: Added a config-driven `request_timeout` (per-attempt network ceiling) so a stalled connection fails in seconds, not minutes.
2. **Transient Retries**: Added `max_retries` + exponential `retry_backoff` for `ConnectionError`/`Timeout`, so brief blips self-recover instead of failing the build.
3. **Honest SLAs**: The response-time gate now times only the *successful* attempt — backoff and failed-attempt latency are excluded, so `max_response_time` still reflects true server performance.
4. **Safety Net**: Added `timeout-minutes: 15` to the CI job so no future hang can run unbounded.

**Principle**: Infrastructure flakiness is managed at the network layer (bounded timeout + retry), never by silencing assertions or inflating performance thresholds.