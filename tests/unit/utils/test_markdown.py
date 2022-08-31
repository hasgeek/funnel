"""Tests for markdown parser."""

from difflib import ndiff

from markupsafe import Markup
import pytest

from funnel.utils.markdown import markdown
from funnel.utils.markdown.testhelpers import get_md_test_data


def test_markdown_none() -> None:
    assert markdown(None) is None


def test_markdown_blank() -> None:
    assert markdown('') == Markup('')


@pytest.mark.parametrize(('ref_html', 'result'), get_md_test_data())
def test_markdown_dataset(ref_html: str, result: str) -> None:
    if ref_html != result:
        difference = ndiff(ref_html.split('\n'), result.split('\n'))
        msg = []
        for line in difference:
            if line.startswith(' '):
                msg.append(line)
        pytest.fail("\n".join(msg), pytrace=False)
