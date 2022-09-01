"""Tests for markdown parser."""

from difflib import context_diff

from markupsafe import Markup
import pytest

from funnel.utils.markdown import markdown
from funnel.utils.markdown.testhelpers import get_md_test_dataset, get_md_test_output


def test_markdown_none() -> None:
    assert markdown(None) is None


def test_markdown_blank() -> None:
    assert markdown('') == Markup('')


@pytest.mark.parametrize(
    (
        'case_id',
        'config_id',
    ),
    get_md_test_dataset(),
)
def test_markdown_dataset(case_id: str, config_id: str) -> None:
    (expected_output, output) = get_md_test_output(case_id, config_id)
    if expected_output != output:
        difference = context_diff(expected_output.split('\n'), output.split('\n'))
        msg = []
        for line in difference:
            if not line.startswith(' '):
                msg.append(line)
        pytest.fail(
            '\n'.join(
                [
                    f'Markdown output failed. File: {case_id}.toml, Config key: {config_id}.',
                    'Please check tests/data/markdown/output.html for detailed output comparision',
                ]
                + msg
            ),
            pytrace=False,
        )
