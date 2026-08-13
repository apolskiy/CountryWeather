# Define artifact directories
TEST_DIR := test_results
ALLURE_DIR := allure-results
REPORT_DIR := allure-report

# Extra flags forwarded verbatim to pytest, e.g. PYTEST_ARGS="-v --env=countries"
PYTEST_ARGS ?=

# Every tracked Python file, enumerated from git rather than listed here: a
# hand-maintained list silently stops covering a directory the day someone
# forgets to add it.
# Deliberately '=' rather than ':=': evaluated when the lint recipe uses it,
# so 'make test' and 'make clean' do not shell out to git for nothing.
PY_FILES = $(shell git ls-files '*.py')

.PHONY: clean
clean:
	@echo "--- Cleaning up previous artifacts ---"
	@rm -rf $(TEST_DIR) $(ALLURE_DIR) $(REPORT_DIR) .pytest_cache
	@echo "Cleanup complete."

.PHONY: lint
lint:
	@echo "--- Running Pylint (gate: 10.00/10) ---"
	@pylint --fail-under=10 $(PY_FILES)

.PHONY: test
test: clean
	@echo "--- Preparing environment ---"
	@mkdir -p $(TEST_DIR) $(ALLURE_DIR)
	@echo "--- Running tests ---"
	@pytest tests/ \
		--junitxml=$(TEST_DIR)/results.xml \
		--html=$(TEST_DIR)/report.html \
		--self-contained-html \
		--alluredir=$(ALLURE_DIR) $(PYTEST_ARGS)
	@echo "--- Test execution complete ---"