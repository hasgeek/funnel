# Managing Test cases and data

-   Run `flask update_test_data` to generate test data whenever code changes or test cases/configs are added, updated or deleted.
-   Expected markdown output will be generated in `tests/data/markdown/output.html`.
    -   This will overwrite "all" expected results with the current output of markdown.
-   Test cases are placed in the `tests/data/markdown` folder in `.toml` files.

# Creating a new test case

-   Copy `test_case_id.toml.sample` to `your_test_case.toml`
-   Update the data and configuration for the test case
-   Run `flask update_test_data`

## Precautions

-   Before working on any code changes or test case/config updates for `funnel.utils.markdown`, please make sure there are no failing tests.
-   Once you change anything in the markdown logic or it's test cases/configs, the consequence of doing so by checking the output of failing tests.
    -   This will give you a complete overview of the exact consequences of the changes you made.
-   If the changes align with what you intend, once you are ready to commit the changes made, please run `flask update_test_data` and run tests again to check if they are now passing.

# Tests output results

Whenever the tests are run, the resultant output for each case will be updated in `tests/data/markdown/output.html`
