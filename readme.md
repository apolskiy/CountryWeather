To be able to deploy teh project from github onto a remote ubuntu server:
Configured .gthub/workflows/ci.yml to run on push to any branch.


Project Structure:

config/: Houses all environment, infrastructure, and static inventory configuration files.

.github/workflows/: Contains the CI/CD pipeline definitions.

tests/: Contains the business logic and test cases.

validators/: Contains schema enforcement classes (Pydantic/Dataclasses)
utils/:
Original Claude prompt:
"Using the rules defined in .claude/rules/framework-rules.md, generate the config/environments.yaml file. Ensure the schema strictly matches the requirements: two environments ('countries', 'weather') with base_urls, max_response_time, and min_results_count. No other values should be added."

To generate view allure reports in windows (outside of result files via python): use allure serve allure-results

If allure is not installed from PowerShell use command: scoop install allure
scoop install allure


If scoop is not installed use the following commands in powershell to install it:
Set-ExecutionPolicy RemoteSigned -scope CurrentUser
irm get.scoop.sh | iex

To install allure on ubuntu, use : sudo apt install allure



CountryWeather directory structure/
├── .claude/                  # AI Governance & Coding Standard <br>
│   ├── rules/                # Constraints for AI behavior <br>
│   └── skills/               # Reusable test-generation templates <br>
├── .github/                  # CI/CD Orchestration <br>
│   └── workflows/<br>
│       └── ci.yml            # Pipeline definition <br>
├── config/                   # Static Configuration Data <br>
│   ├── environments.yaml     # API endpoints & test thresholds <br>
│   └── targets.json          # Infrastructure inventory (OS/IP list) <br>
├── test_results/             # Artifacts: JUnit XML & HTML reports <br>
├── allure-results/           # Artifacts: Raw Allure test data <br>
├── allure-report/            # Artifacts: Generated Allure HTML report <br>
├── tests/                    # Core Test Logic <br>
│   ├── test_countries.py     # Functional test suite <br>
│   └── test_weather.py       # Functional test suite
├── utils/                    # Shared Infrastructure <br>
│   └── api_client.py         # HTTP abstraction & logging
├── validators/               # Schema Enforcement <br>
│   ├── __init__.py           # Package declaration <br>
│   ├── country_validator.py  # Pydantic/Jsonschema logic <br>
│   └── weather_validator.py  # Pydantic/Jsonschema logic <br>
├── test_data/                # Static data fixtures <br>
├── .gitignore                # Version control exclusions <br>
├── conftest.py               # Runtime fixtures & pytest hooks (Root) <br>
├── requirements.txt          # Environment dependencies <br>
├── CLAUDE_LOG.md             # Engineering decision journal <br>
└── README.md                 # Project documentation <br>



Correction prompt to refactor the files include doc strings, function annotations, type hints without changing the logic:
""I need to perform a quality audit on the existing codebase. Refactor every Python file in the utils/, tests/, and validators/ directories to strictly comply with the framework-rules.md documentation standards.

Add Google-style docstrings to every module, class, and method.

Ensure every docstring has Args: and Returns: sections.

Verify all type hints are present.

Ensure no pylint C0111, C0114, or C0116 warnings would trigger.

Do not change the logic—only improve the documentation and annotations."