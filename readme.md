Aleksandr Polskiy

# CountryWeather API Automation Framework

A robust Quality Engineering framework designed for testing UCaaS/CCaaS-style API architectures. Features automated schema enforcement, data-driven test generation, and detailed Allure reporting.

> **Documentation status:** describes **v1.3.1**, reviewed 2026-08-18.
> Each section below carries the release and date its content last changed, so a
> reader arriving at a later version can see at a glance which parts moved. This
> file always describes the *current* release; release-to-release history lives
> in [CHANGELOG.md](CHANGELOG.md).

## 1. Project Structure

<sub>v1.0.0 &middot; 2026-08-10</sub>

```text
CountryWeather/
├── .claude/                  # AI governance: coding rules and generator skills
│   ├── rules/                # code-style, framework-rules, testing-standards
│   └── skills/               # CLAUDE_LOG.md plus test/validator generators
├── .github/workflows/ci.yml  # CI pipeline: serialized, Make-driven
├── config/
│   └── environments.yaml     # Per-environment URLs, thresholds, retry policy
├── test_data/                # Single source of truth
│   └── master_entities.json  # Consolidated country/city/coord data
├── tests/                    # Data-driven functional tests
│   ├── test_countries.py
│   └── test_weather.py
├── utils/
│   └── api_client.py         # Shared HTTP client: auth, retries, pacing, SLA
├── validators/               # Dataclass schema enforcement
│   ├── country_schema.py
│   └── weather_schema.py
├── conftest.py               # pytest_generate_tests parametrization hook
├── pytest.ini                # Pytest configuration
├── .pylintrc                 # Static analysis configuration
├── Makefile                  # The canonical invocation, shared by local and CI
├── requirements.txt          # Project dependencies
├── CHANGELOG.md              # Release-to-release history
└── readme.md
```

Generated at run time and gitignored: `allure-results/`, `allure-report/`, and
`test_results/` (JUnit XML plus the self-contained HTML report). `make clean`
removes all of them, and `make test` runs `clean` first, so a run never reports
against a previous run's artifacts.

> Two files, `test_results/report.html` and `test_results/results.xml`, were
> committed before the ignore rule was added and are therefore still tracked -
> `.gitignore` does not untrack what git already knows about. `make clean`
> deletes them, so a local `make test` leaves two deletions in `git status` that
> have nothing to do with the change being worked on. Untracking them with
> `git rm --cached` resolves it; they are build output, and the ignore rule
> already says they were never meant to be in the repository.

## 2. Setup & Installation

<sub>v1.0.0 &middot; 2026-08-10</sub>

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

<sub>v1.2.0 &middot; 2026-08-13</sub>

```bash
pytest tests/                 # full suite (countries + weather)
pytest tests/ --env=countries # REST Countries only (requires the API key)
pytest tests/ --env=weather   # Open-Meteo only (no key, no quota usage)
```

### Make Targets

A `Makefile` wraps the canonical pytest invocation so local runs and CI execute
the identical command. This is the single source of truth for the pytest flags
and the artifact directories.

```bash
make lint                              # pylint over every tracked .py file, gated at 10.00/10
make test                              # clean artifacts, then run the full suite
make clean                             # remove test_results, allure-results, allure-report, .pytest_cache
make test PYTEST_ARGS="--env=weather"  # forward extra flags to pytest
```

`make test` runs `clean` first, so each run starts from a fresh set of artifact
directories. The `PYTEST_ARGS` variable forwards any additional pytest flags
(for example `-v` or `--env=<suite>`) without editing the recipe.

`make lint` is the same command CI runs, and it needs no API key and spends no
quota - so it is the cheap check to run before pushing. The file list comes from
`git ls-files '*.py'` rather than a list in the recipe, so a new module is
covered the moment it is tracked.

> The file was originally generated as `MakeFIle` and has been corrected to
> `Makefile`. The exact name matters: GNU make only auto-discovers `GNUmakefile`,
> `makefile`, or `Makefile`. Any other casing resolves locally on a
> case-insensitive filesystem but fails on the case-sensitive `ubuntu-latest`
> runner with "No targets specified and no makefile found".

## 4. Data-Driven Architecture

<sub>v1.0.0 &middot; 2026-08-10</sub>

This project uses a **Single Source of Truth** pattern.

* All geographic and weather entity data is consolidated in `test_data/master_entities.json`.
* Tests are parametrized centrally by a `pytest_generate_tests` hook in `conftest.py`: any test
  declaring an `entity` argument is automatically run against every record in the dataset.
* **Benefit**: Adding a new country to the JSON expands coverage for both the Countries and Weather
  API suites automatically - no code changes required.

## 5. API Client & Network Resilience

<sub>v1.0.0 &middot; 2026-08-10</sub>

All HTTP traffic flows through the shared `utils/api_client.py` wrapper, which centralizes
cross-cutting concerns and keeps test files focused on functional assertions.

* **Authentication**: Bearer-token injection for the environment that declares an `auth_env_var`.
* **Envelope handling**: `get_objects()` unwraps the v5 `data.objects` envelope and paginates list
  endpoints (page size capped at 100 by the API).
* **Timeout & retries**: A hard per-attempt `request_timeout` prevents indefinite hangs; transient
  `ConnectionError`/`Timeout` failures and retryable statuses (`429` rate-limiting, `502/503/504`)
  are retried with exponential backoff, honouring the server's `Retry-After` header. All thresholds
  live in `config/environments.yaml` - zero inline defaults.
  Elected to use request library directly intead of urllib3 Retry or tenacity due external API limits
  on concurrency and frequency of requests. There was also a hard cap on maximum APU requests per month,
  so this was beneficial in curb unnecessary retries, which carry a real cost with cap limits.
  As API provider limited number of requests per IP, it made sense to avoid running tests in parallel,
  using pytest-xdist, in order to avoid a cascade of failures, which would have nothing to do with application
  under test.
* **Proactive pacing**: For the same rate-limit reasons, a config-driven `min_request_interval` enforces a
  minimum gap between consecutive requests, staying under the provider's short-window burst limit *before*
  a `429` is ever returned - cheaper than reacting with retries against a capped monthly quota. The pacing
  clock is shared session-wide across the per-test client instances, which is only sound because the suite
  runs serially (see the pytest-xdist decision above); the `429`/`Retry-After` backoff remains as a fallback.

* **Performance gate**: Each call asserts against `max_response_time`, timing only the successful
  attempt so the SLA reflects real server latency rather than retry/backoff overhead.

## 6. CI/CD Pipeline

<sub>v1.2.0 &middot; 2026-08-13</sub>

Configured for GitHub Actions (`.github/workflows/ci.yml`) on `ubuntu-latest`.
Two jobs: `lint`, then `test`, which declares `needs: lint`.

* **Execution**: The workflow invokes `make lint` and `make test`, so CI runs the
  exact same commands as a local run. The workflow forwards `-v` (and
  `--env=<suite>` when a manual `workflow_dispatch` run selects a single suite)
  via `PYTEST_ARGS`.
* **Static analysis gates the suite**: `make lint` runs `pylint --fail-under=10`
  over every tracked `.py` file, and the test job does not start unless it
  passes. The ordering is the quota argument again: the linter needs no API key
  and spends nothing, so a failure there costs seconds, whereas running the
  suite first would spend capped monthly requests to learn something static
  analysis already knew. `--fail-under=10` rather than a softer floor, because a
  score permitted to drift is not a gate - it never fails a build, it just gets
  quietly worse.
* **Triggered only by changes that can alter the result**: the workflow
  originally ran on *every* push and pull request to any branch, which meant a
  commit touching nothing but Markdown still ran the full suite against the live
  REST Countries API and spent monthly quota to re-confirm a result that could
  not have moved. Since the scarce resource here is that quota rather than
  runner minutes (see §5 and *Serialized runs* below), the trigger now carries a
  `paths-ignore` list covering `**.md`, `LICENSE`, `.gitignore` and `.idea/**`.
  This is a denylist rather than an allowlist on purpose: an allowlist has to be
  extended whenever a directory is added, and forgetting is silent - new code
  that never runs in CI while the badge stays green. A denylist fails the other
  way, and an unnecessary run costs quota once and is visible. Use
  `workflow_dispatch` to force a run regardless.
* **Serialized runs**: A top-level `concurrency` group with a constant,
  branch-agnostic name serializes every run of the workflow account-wide, with
  `cancel-in-progress: false` so an in-flight run finishes before the next
  starts. Because the REST Countries quota and burst limit are shared across all
  branches, this prevents two runs from racing the same API and re-triggering the
  rate limiting that the request pacing (see §5) is designed to avoid. A
  per-branch group would not be sufficient, since the limit is not scoped to a
  branch.
* **Thresholds**: Enforces strict per-environment performance thresholds (countries 5.0s / weather
  3.0s) to monitor API latency regressions.
* **Reliability**: A hard request timeout plus a job-level `timeout-minutes: 15` guard ensure a
  stalled upstream can never hang the pipeline; transient blips self-recover via retries.
* **Robustness**: Artifact persistence on failure (`if: always()`) captures JUnit/Allure reports for
  debug review even when assertions fail.

## 7. Test Identity

<sub>v1.3.1 &middot; 2026-08-18</sub>

Every test carries an assigned, stable identifier:

```python
@pytest.mark.test_id("CWA_10001")
@allure.story("Country by Name - Schema and Data Integrity")
def test_country_by_name(self, api_client_fixture: ApiClient, entity: dict) -> None:
```

IDs run from `CWA_10001` and are **never reused** - deleting a test retires its
number rather than freeing it. The suite currently occupies `CWA_10001` to
`CWA_10009`; the next free identifier is `CWA_10010`.

The identifier exists because **a test's name is not a stable identity**. Any
store keyed on the name forks a test's history the moment it is renamed, turning
one test with a long record into two with short ones - and doing so silently,
since both halves still look like valid tests. Naming is supposed to be free to
improve, and this is what makes it free.

`conftest.py` republishes the marker into both report formats at collection
time, in `_publish_test_ids`: as an Allure label and as a JUnit `<property>`.
Collection time rather than a fixture, so the label is attached before any
reporter starts building a result and cannot be lost to fixture ordering. The
marker is authored once and lands wherever it is needed.

The consumer is
[PortfolioTestInsights](https://github.com/apolskiy/PortfolioTestInsights),
which keeps this suite's results past GitHub's 90-day artifact retention. An ID
observed anywhere for a test becomes that test's identity **everywhere**,
including on rows recorded before the ID existed, so history from before the
scheme stitches to history from after.

Worth stating what that is not, because the obvious implementation is wrong and
was tried first. Keying on `COALESCE(test_id, test_uid)` splits each test in two
at the moment IDs arrive - every earlier row keyed by uid, every later row keyed
by ID - producing two short histories where there was one long one, which is the
precise failure the IDs exist to prevent.

## 8. Engineering Principles

<sub>v1.2.0 &middot; 2026-08-13</sub>

* **Isolation**: Function-scoped fixtures give each test its own client instance. The suite runs
  serially by design (see §5) rather than under pytest-xdist, so the one piece of shared session-wide
  state - the request-pacing clock - stays correct without cross-process coordination.
* **Governance**: Code generation is governed by local AI rules files in `.claude/rules/` -
  `framework-rules.md` (architectural constraints), `testing-standards.md` (test authoring), and
  `code-style.md` (naming, typing, layout) - to ensure Pylint/type-hinting compliance and
  Google-style docstrings. Those rules are stated for a generator to follow; the CI lint gate (§6)
  is what makes them binding, since a convention nothing checks is a preference.
* **Integrity**: Latency thresholds are enforced as code; infrastructure flakiness is treated as a
  risk to be managed (bounded timeout + retry), not a test to be silenced.
