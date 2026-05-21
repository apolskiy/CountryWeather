Aleksandr Polskiy<br>
1. Project Structure
CountryWeather/<br>
├── .claude/                  # AI Governance & Coding Standards<br>
├── .github/workflows/        # CI/CD Pipeline Definitions<br>
├── config/                   # Environments.yaml & static config<br>
├── tests/                    # Core Functional Test Logic<br>
├── utils/                    # Shared HTTP API Client<br>
├── validators/               # Pydantic Schema Enforcement<br>
├── allure-results/           # Raw Test Data<br>
├── allure-report/            # Generated HTML Reports<br>
└── requirements.txt          # Project Dependencies<br>
2. Setup & Installation
Prerequisites
Python 3.14.5

Allure Commandline (for report generation)

Installation
Clone the repository.

Create a virtual environment:

Bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:

Bash
   pip install -r requirements.txt
Allure Reporting Setup
Ubuntu/Linux: sudo apt install allure

Windows (via Scoop):

PowerShell
    Set-ExecutionPolicy RemoteSigned -scope CurrentUser
    irm get.scoop.sh | iex
    scoop install allure
    ```

## 3. Usage
Run the test suite using `pytest`. You can filter by environment (countries/weather) or run all:

```bash
# Run all tests
pytest tests/

# Run specific environment
pytest tests/ --env=countries
To view reports locally after a test run:

Bash
allure serve allure-results
4. CI/CD Pipeline
This project is configured for GitHub Actions (.github/workflows/ci.yml).

Triggers: Automatically runs on push to any branch and manual workflow_dispatch.

Artifacts: Automatically generates and uploads JUnit XML and Allure HTML reports for every run.

Runner: Configured for ubuntu-latest (GitHub Cloud Runner).

5. Engineering Notes & Configuration
Performance Thresholds
The framework enforces strict response time thresholds defined in config/environments.yaml 
(max_response_time: 2.0 for Countries, 3.0 for Weather).

Note on CI Latency:
Because this project uses public GitHub cloud runners, network variability can occasionally 
trigger false-negative AssertionError failures. If you observe flakiness during CI runs, ensure
your local environment thresholds are appropriately tuned, or consider migrating to a self-hosted 
runner if strict latency validation is a primary requirement.
Just in case tested with 5.0 timeouts tests work. In case of flaky tests detailed log analisys 
tools may be necessary.