Aleksandr Polskiy

# CountryWeather API Automation Framework

A robust Quality Engineering framework designed for testing UCaaS/CCaaS-style API architectures. Features automated schema enforcement, data-driven test generation, and detailed Allure reporting.

## 1. Project Structure
```text
CountryWeather/
├── .claude/                  # AI Governance & Coding Standards
├── .github/workflows/        # CI/CD Pipeline Definitions
├── config/                   # environments.yaml & static config
├── test_data/                # Single Source of Truth
│   └── master_entities.json  # Consolidated country/city/coord data
├── tests/                    # Data-driven functional tests
├── utils/                    # Shared HTTP API Client
├── validators/               # Dataclass Schema Enforcement
├── allure-results/           # Raw Test Data
└── requirements.txt          # Project Dependencies
```

## 2. Setup & Installation

### Prerequisites

* Python 3.14.5
* Allure Commandline

### Installation

1. Create a virtual environment: `python3 -m venv venv`
2. Activate: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. Install dependencies: `pip install -r requirements.txt`

### Secrets Configuration

The REST Countries API (v5) requires an API key, which the client reads from the
`RESTCOUNTRIES_API_KEY` environment variable. The key is never hardcoded or committed.

* **Local (bash)**: `export RESTCOUNTRIES_API_KEY=your_key`
* **Local (PowerShell)**: `$env:RESTCOUNTRIES_API_KEY = "your_key"`
* **GitHub Actions**: Add `RESTCOUNTRIES_API_KEY` under **Settings > Secrets and variables > Actions**.

> The Open-Meteo weather API needs no key, so `pytest --env=weather` runs without any secret configured.

### Allure Reporting

* **Ubuntu**: `sudo apt install allure`
* **Windows**: `scoop install allure`
* **View Report**: `allure serve allure-results`

## 3. Running the Suite

```bash
pytest tests/                 # full suite (countries + weather)
pytest tests/ --env=countries # REST Countries only (requires the API key)
pytest tests/ --env=weather   # Open-Meteo only (no key, no quota usage)
```

## 4. Data-Driven Architecture

This project uses a **Single Source of Truth** pattern.

* All geographic and weather entity data is consolidated in `test_data/master_entities.json`.
* Tests are parametrized centrally by a `pytest_generate_tests` hook in `conftest.py`: any test
  declaring an `entity` argument is automatically run against every record in the dataset.
* **Benefit**: Adding a new country to the JSON expands coverage for both the Countries and Weather
  API suites automatically — no code changes required.

## 5. API Client & Network Resilience

All HTTP traffic flows through the shared `utils/api_client.py` wrapper, which centralizes
cross-cutting concerns and keeps test files focused on functional assertions.

* **Authentication**: Bearer-token injection for the environment that declares an `auth_env_var`.
* **Envelope handling**: `get_objects()` unwraps the v5 `data.objects` envelope and paginates list
  endpoints (page size capped at 100 by the API).
* **Timeout & retries**: A hard per-attempt `request_timeout` prevents indefinite hangs; transient
  `ConnectionError`/`Timeout` failures and retryable statuses (`429` rate-limiting, `502/503/504`)
  are retried with exponential backoff, honouring the server's `Retry-After` header. All thresholds
  live in `config/environments.yaml` — zero inline defaults.
* **Performance gate**: Each call asserts against `max_response_time`, timing only the successful
  attempt so the SLA reflects real server latency rather than retry/backoff overhead.

## 6. CI/CD Pipeline

Configured for GitHub Actions (`.github/workflows/ci.yml`) on `ubuntu-latest`.

* **Execution**: Enforces strict per-environment performance thresholds (countries 5.0s / weather
  3.0s) to monitor API latency regressions.
* **Reliability**: A hard request timeout plus a job-level `timeout-minutes: 15` guard ensure a
  stalled upstream can never hang the pipeline; transient blips self-recover via retries.
* **Robustness**: Artifact persistence on failure (`if: always()`) captures JUnit/Allure reports for
  debug review even when assertions fail.

## 7. Engineering Principles

* **Isolation**: No singleton patterns; thread-safe fixtures for parallel execution.
* **Governance**: Code generation is governed by local AI rules files to ensure Pylint/type-hinting
  compliance and Google-style docstrings.
* **Integrity**: Latency thresholds are enforced as code; infrastructure flakiness is treated as a
  risk to be managed (bounded timeout + retry), not a test to be silenced.
