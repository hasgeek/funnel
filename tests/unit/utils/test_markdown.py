"""Tests for markdown parser."""

from typing import List, Tuple
import os

from bs4 import BeautifulSoup
from markupsafe import Markup
import pytest
import toml

from funnel.utils.markdown import markdown
from funnel.utils.markdown.helpers import MD_CONFIGS

DATA_ROOT = os.path.abspath(os.path.join('tests', 'data', 'markdown'))


def test_markdown_none() -> None:
    assert markdown(None) is None


def test_markdown_blank() -> None:
    assert markdown('') == Markup('')


dataset: List[Tuple[str, str]] = []
with open(os.path.join(DATA_ROOT, 'output.html')) as o:
    output = BeautifulSoup(o.read(), 'html.parser')
    file: str
    for file in os.listdir(DATA_ROOT):
        if file.endswith('.toml'):
            with open(os.path.join(DATA_ROOT, file)) as f:
                file_data = toml.load(f)
                data = file_data['data']
                conf = file_data['config']
                results = file_data['results']
                for c in conf['configs']:
                    if c in MD_CONFIGS and c in results:
                        row = output.find(id='_'.join(file.split('.')[:-1] + [c]))
                        result = markdown(data['markdown'], **MD_CONFIGS[c]).__str__()
                        ref_html = results[c].lstrip('\n\r').rstrip(' \n\r')
                        result = result.lstrip('\n\r').rstrip(' \n\r')
                        dataset.append(
                            (
                                ref_html,
                                result,
                            )
                        )
                        if row:
                            row.find_all('td')[3].append(
                                BeautifulSoup(result, 'html.parser')
                            )
    with open(os.path.join(DATA_ROOT, 'output.html'), 'w') as op:
        op.write(output.prettify())


@pytest.mark.parametrize(('ref_html', 'result'), dataset)
def test_dataset(ref_html, result) -> None:
    assert ref_html == result
