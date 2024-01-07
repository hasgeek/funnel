"""Tests for markdown parser."""

import pytest
from markupsafe import Markup

from funnel.utils.markdown import MarkdownConfig


def test_markdown_none() -> None:
    assert MarkdownConfig.registry['basic'].render(None) is None
    assert MarkdownConfig.registry['document'].render(None) is None
    assert MarkdownConfig.registry['inline'].render(None) is None
    assert MarkdownConfig().render(None) is None


def test_markdown_blank() -> None:
    blank_response = Markup('')
    assert MarkdownConfig.registry['basic'].render('') == blank_response
    assert MarkdownConfig.registry['document'].render('') == blank_response
    assert MarkdownConfig.registry['inline'].render('') == blank_response
    assert MarkdownConfig().render('') == blank_response


def test_markdown_cases(
    md_testname: str, md_configname: str, markdown_test_registry
) -> None:
    case = markdown_test_registry.test_case(md_testname, md_configname)
    if case.expected_output is None:
        pytest.fail(f'Expected output not known for {case}')

    assert case.expected_output == case.output

    # Debug function
    # fail_with_diff(case.expected_output, case.output)


@pytest.mark.debug_markdown_output()
def test_markdown_debug_output(pytestconfig, markdown_test_registry) -> None:
    has_mark = pytestconfig.getoption('-m', default=None) == 'debug_markdown_output'
    if not has_mark:
        pytest.skip('Skipping update of debug output file for markdown test cases')
    markdown_test_registry.update_debug_output()
