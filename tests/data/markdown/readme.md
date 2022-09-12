# Managing test cases

-   Test cases are maintained in the folder `tests/data/markdown` in `.toml` files.
-   To add a new test case:
    -   Run `pytest -k "test_markdown"` to ensure there are no existing tests failing.
    -   Copy `test_case_id.toml.sample` to `new_test_case.toml`.
    -   Update the data and configuration for the test case.
    -   Run `make tests-data-md` to generate expected output.
    -   This will update `new_test_case.toml` with the expected output.
-   Run `make tests-data-md` to generate test data whenever code changes or test cases/configs are added, updated or deleted.
-   Expected markdown output will be generated in `tests/data/markdown/output.html`.
    -   This will overwrite "all" expected results with the current output of markdown.

# How does `update_markdown_data` work?

Running `make tests-data-md` cycles through each `.toml` file and does the following:

1.  Loads the data (`[data.markdown]`) and the different configurations to run the test case with.
1.  Configurations could be amongst the predefined ones (`[config.configs]`) or custom defined within the `.toml` file (`[config.extra_configs]`).
1.  Generates the current output of `markdown()` for each configuration and stores them in (`[results]`).
1.  Dumps this data back to the `.toml` file.

# Precautions

-   Before working on any code changes or test case/config updates for `funnel.utils.markdown`, please make sure there are no failing tests.
-   Once you change anything in the markdown logic or it's test cases/configs, the result of doing so can be checked in the output of failing tests.
    -   This will give you a complete overview of the exact consequences of the changes you made.
    -   If no tests failed, it means there was no change in output.
-   If the changes align with what you intend, once you are ready to commit the changes made, please run `make tests-data-md` and run tests again to check if they are now passing.

# Scenarios

Tests can fail in the following scenarios.

-   New test data is added or a test data has been updated or a configuration has been added/changed for a test case, but expected output has not been generated.
    -   The test case will fail until expected output is generated.
-   After running a package upgrade.
    -   There is either a change in output or `markdown()` is breaking due to some change in some package.
    -   If there is a change in output, review and evaluate if the change is acceptable and devise PoA accordingly.

Undetected changes can happen in the following scenarios.

-   If the precautions mentioned above are not followed.

# Tests output results

Whenever the tests are run, the expected output alongwith the current output for each case-configuration combination will be updated in `tests/data/markdown/output.html`.
