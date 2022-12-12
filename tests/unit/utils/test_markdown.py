"""Tests for markdown parser."""
# pylint: disable=too-many-arguments

import warnings

from markupsafe import Markup
import pytest

from funnel.utils.markdown import MarkdownConfig, markdown


def test_markdown_none() -> None:
    assert markdown(None, 'basic') is None
    assert markdown(None, 'document') is None
    assert markdown(None, 'inline') is None
    assert markdown(None, MarkdownConfig()) is None


def test_markdown_blank() -> None:
    blank_response = Markup('')
    assert markdown('', 'basic') == blank_response
    assert markdown('', 'document') == blank_response
    assert markdown('', 'inline') == blank_response
    assert markdown('', MarkdownConfig()) == blank_response


# @pytest.mark.parametrize(
#     ('md_testname', 'md_configname'),
#     MarkdownTestRegistry.test_cases(),
# )
# def test_markdown_cases(md_testname: str, md_configname: str, unified_diff_output) -> None:
def test_markdown_cases(
    md_testname: str, md_configname: str, markdown_test_registry
) -> None:
    case = markdown_test_registry.test_case(md_testname, md_configname)
    if case.expected_output is None:
        warnings.warn(f'Expected output not generated for {case}')
        pytest.skip(f'Expected output not generated for {case}')

    assert case.expected_output == case.output

    # Debug function
    # unified_diff_output(case.expected_output, case.output)


@pytest.mark.update_markdown_data()
def test_markdown_update_output(pytestconfig, markdown_test_registry):
    """Update the expected output in all .toml files."""
    has_mark = pytestconfig.getoption('-m', default=None) == 'update_markdown_data'
    if not has_mark:
        pytest.skip('Skipping update of expected output of markdown test cases')
    markdown_test_registry.update_expected_output()


@pytest.mark.debug_markdown_output()
def test_markdown_debug_output(pytestconfig, markdown_test_registry):
    has_mark = pytestconfig.getoption('-m', default=None) == 'debug_markdown_output'
    if not has_mark:
        pytest.skip('Skipping update of debug output file for markdown test cases')
    markdown_test_registry.update_debug_output()
