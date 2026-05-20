

Project Structure:

config/: Houses all environment, infrastructure, and static inventory configuration files.

.github/workflows/: Contains the CI/CD pipeline definitions.

tests/: Contains the business logic and test cases.

validators/: Contains schema enforcement classes (Pydantic/Dataclasses)
utils/:
Original Claude prompt:
"Using the rules defined in .claude/rules/framework-rules.md, generate the config/environments.yaml file. Ensure the schema strictly matches the requirements: two environments ('countries', 'weather') with base_urls, max_response_time, and min_results_count. No other values should be added."



CountryWeather directory structure/
├── .claude/                  # AI Governance & Coding Standards
│   ├── rules/                # Constraints for AI behavior
│   └── skills/               # Reusable test-generation templates
├── .github/                  # CI/CD Orchestration
│   └── workflows/
│       └── ci.yml            # Pipeline definition
├── config/                   # Static Configuration Data
│   ├── environments.yaml     # API endpoints & test thresholds
│   └── targets.json          # Infrastructure inventory (OS/IP list)
├── test_results/             # Artifacts: JUnit XML & HTML reports
├── allure-results/           # Artifacts: Raw Allure test data
├── allure-report/            # Artifacts: Generated Allure HTML report
├── tests/                    # Core Test Logic
│   ├── test_countries.py     # Functional test suite
│   └── test_weather.py       # Functional test suite
├── utils/                    # Shared Infrastructure
│   └── api_client.py         # HTTP abstraction & logging
├── validators/               # Schema Enforcement
│   ├── __init__.py           # Package declaration
│   ├── country_validator.py  # Pydantic/Jsonschema logic
│   └── weather_validator.py  # Pydantic/Jsonschema logic
├── test_data/                # Static data fixtures
├── .gitignore                # Version control exclusions
├── conftest.py               # Runtime fixtures & pytest hooks (Root)
├── requirements.txt          # Environment dependencies
├── CLAUDE_LOG.md             # Engineering decision journal
└── README.md                 # Project documentation



Correction prompt to refactor the files include doc strings, function annotations, type hints without changing the logic:
""I need to perform a quality audit on the existing codebase. Refactor every Python file in the utils/, tests/, and validators/ directories to strictly comply with the framework-rules.md documentation standards.

Add Google-style docstrings to every module, class, and method.

Ensure every docstring has Args: and Returns: sections.

Verify all type hints are present.

Ensure no pylint C0111, C0114, or C0116 warnings would trigger.

Do not change the logic—only improve the documentation and annotations."