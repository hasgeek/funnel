"""Tests for markdown parser."""
# pylint: disable=too-many-arguments

from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import warnings

from bs4 import BeautifulSoup
from markupsafe import Markup
import pytest
import tomlkit

from funnel.utils.markdown import MarkdownConfig, markdown

DATAROOT: Path = Path('tests/data/markdown')


class MarkdownCase:
    """Class for markdown test case for a content-profile combination."""

    def __init__(
        self,
        test_id: str,
        mdtext: str,
        configname: str,
        config: Optional[Dict] = None,
        expected_output: Optional[str] = None,
    ) -> None:
        self.test_id = test_id
        self.mdtext = mdtext
        self.configname = configname
        self.config = MarkdownConfig(**config) if config else None
        self.expected_output = expected_output

    def __repr__(self) -> str:
        return self.caseid

    @property
    def caseid(self) -> str:
        return f'{self.test_id}-{self.configname}'

    @property
    def markdown_config(self) -> Union[str, MarkdownConfig]:
        """
        Return the markdown config for the test case.

        Output is str if the config is pre-defined,
        else a custom class inherited from MarkdownConfig.
        """
        return self.config if self.config is not None else self.configname

    @property
    def output(self) -> str:
        return markdown(self.mdtext, self.config or self.configname)

    def update_expected_output(self) -> None:
        self.expected_output = self.output


class MarkdownTestRegistry:
    test_map: Optional[Dict[str, Dict[str, MarkdownCase]]] = None
    test_files: Dict[str, tomlkit.TOMLDocument]

    @classmethod
    def load(cls) -> None:
        """Load test cases from .toml files and create a 2D map."""
        if cls.test_map is None:
            cls.test_map = {}
            cls.test_files = {
                file.name: tomlkit.loads(file.read_text())
                for file in DATAROOT.iterdir()
                if file.suffix == '.toml'
            }
            for test_id, test_data in cls.test_files.items():
                config = test_data['config']
                exp = test_data.get('expected_output', {})
                # Combine pre-defined profiles with custom profiles
                # and store each test case in test_map[test_id][configname]
                cls.test_map[test_id] = {
                    configname: MarkdownCase(
                        test_id=test_id,
                        mdtext=test_data['markdown'],
                        configname=configname,
                        config=config,
                        expected_output=Markup(exp.get(configname, None)),
                    )
                    for configname, config in {
                        **{p: None for p in config.get('profiles', [])},
                        **config.get('custom_profiles', {}),
                    }.items()
                }

    @classmethod
    def dump(cls) -> None:
        if cls.test_map is not None:
            for test_id, data in cls.test_files.items():
                data['expected_output'] = {
                    configname: tomlkit.api.string(case.output, multiline=True)
                    for configname, case in cls.test_map[test_id].items()
                }
                (DATAROOT / test_id).write_text(tomlkit.dumps(data))

    @classmethod
    def test_cases(cls) -> List[Tuple[str, str]]:
        cls.load()
        return (
            [
                (test_id, configname)
                for test_id, test in cls.test_map.items()
                for configname in test.keys()
            ]
            if cls.test_map is not None
            else []
        )

    @classmethod
    def test_case(cls, test_id: str, configname: str) -> MarkdownCase:
        return cls.test_map[test_id][configname]  # type: ignore[index]

    @classmethod
    def update_expected_output(cls) -> None:
        cls.load()
        cls.dump()

    @classmethod
    def update_debug_output(cls) -> None:
        """Save test output in file output.html for visual debugging."""
        cls.load()
        template = BeautifulSoup(
            (DATAROOT / 'template.html').read_text(), 'html.parser'
        )
        case_template = template.find(id='output_template')
        for test_id, configname in cls.test_cases():
            case: MarkdownCase = cls.test_case(test_id, configname)
            op = copy(case_template)
            del op['id']
            op.select('.filename')[0].string = case.test_id
            op.select('.profile')[0].string = str(case.configname)
            op.select('.config')[0].string = ''
            op.select('.markdown .output')[0].append(case.mdtext)
            op.select('.expected .output')[0].append(
                BeautifulSoup(case.expected_output, 'html.parser')
                if case.expected_output is not None
                else 'Not generated'
            )
            op.select('.final_output .output')[0].append(
                BeautifulSoup(case.output, 'html.parser')
            )
            op['class'] = op.get('class', []) + [
                'success' if case.expected_output == case.output else 'failed'
            ]
            template.find('body').append(op)
        template.find(id='generated').string = datetime.now().strftime(
            '%d %B, %Y %H:%M:%S'
        )
        (DATAROOT / 'output.html').write_text(template.prettify())


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


@pytest.mark.parametrize(
    ('test_id', 'configname'),
    MarkdownTestRegistry.test_cases(),
)
# def test_markdown_cases(test_id: str, configname: str, unified_diff_output) -> None:
def test_markdown_cases(test_id: str, configname: str) -> None:
    case: MarkdownCase = MarkdownTestRegistry.test_case(test_id, configname)
    if case.expected_output is None:
        warnings.warn(f'Expected output not generated for {case}')
        pytest.skip(f'Expected output not generated for {case}')

    assert case.expected_output == case.output

    # Debug function
    # unified_diff_output(case.expected_output, case.output)


@pytest.mark.update_markdown_data()
def test_markdown_update_output(pytestconfig):
    """Update the expected output in all .toml files."""
    has_mark = pytestconfig.getoption('-m', default=None) == 'update_markdown_data'
    if not has_mark:
        pytest.skip('Skipping update of expected output of markdown test cases')
    MarkdownTestRegistry.update_expected_output()


@pytest.mark.debug_markdown_output()
def test_markdown_debug_output(pytestconfig):
    has_mark = pytestconfig.getoption('-m', default=None) == 'debug_markdown_output'
    if not has_mark:
        pytest.skip('Skipping update of debug output file for markdown test cases')
    MarkdownTestRegistry.update_debug_output()
