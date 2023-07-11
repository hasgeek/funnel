"""Tests for MarkdownString and markdown_escape."""

from funnel.utils import MarkdownString, markdown_escape


def test_markdown_escape() -> None:
    """Test that markdown_escape escapes Markdown punctuation (partial test)."""
    assert isinstance(markdown_escape(''), MarkdownString)
    assert markdown_escape('No escape') == 'No escape'
    assert (
        markdown_escape('This _has_ Markdown markup') == r'This \_has\_ Markdown markup'
    )
    mixed = 'This <em>has</em> **mixed** markup'
    assert markdown_escape(mixed) == r'This \<em\>has\<\/em\> \*\*mixed\*\* markup'
    assert markdown_escape(mixed).unescape() == mixed
