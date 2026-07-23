# Define artifact directories
TEST_DIR := test_results
ALLURE_DIR := allure-results
REPORT_DIR := allure-report

# Extra flags forwarded verbatim to pytest, e.g. PYTEST_ARGS="-v --env=countries"
PYTEST_ARGS ?=

.PHONY: clean
clean:
	@echo "--- Cleaning up previous artifacts ---"
	@rm -rf $(TEST_DIR) $(ALLURE_DIR) $(REPORT_DIR) .pytest_cache
	@echo "Cleanup complete."

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