# Managing Test cases and data

-   Run `update_test_data.py` to generate test data during initialisation and whenever test cases are added, updated or deleted
-   Expected markdown output will be generated in `tests/data/markdown/output.html`
-   Test cases are placed in the `tests/data/markdown` folder in `.toml` files.

# Creating a new test case

-   Copy `test_case_id.toml.sample` to `your_test_case.toml`
-   Update the data and configuration for the test case
-   Run `update_test_data.py`

# Tests output results

Whenever the tests are run, the resultant output for each case will be updated in `tests/data/markdown/output.html`
