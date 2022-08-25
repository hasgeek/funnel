"""Tests for markdown parser."""

from typing import List, Tuple
import os

from markupsafe import Markup
import pytest
import toml

from funnel.utils.markdown import markdown

DATA_ROOT = os.path.abspath(os.path.join('tests', 'unit', 'utils', 'data', 'markdown'))


def test_markdown_none() -> None:
    assert markdown(None) is None


def test_markdown_blank() -> None:
    assert markdown('') == Markup('')


dataset: List[Tuple[str, str]] = []
file: str
for file in os.listdir(DATA_ROOT):
    if file.endswith('.toml'):
        with open(os.path.join(DATA_ROOT, file)) as f:
            data = toml.load(f)['data']
            dataset.append(
                (
                    data['md'].lstrip('\n\r').rstrip(' \n\r'),
                    data['html'].lstrip('\n\r').rstrip(' \n\r'),
                )
            )


@pytest.mark.parametrize(('md', 'html'), dataset)
def test_dataset(md, html) -> None:
    assert markdown(md) == html + '\n'
