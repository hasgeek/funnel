"""Tests for markdown parser."""

from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type, Union
import warnings

from bs4 import BeautifulSoup
from markupsafe import Markup
import pytest
import tomlkit

from funnel.utils.markdown import MarkdownProfile, markdown

DATAROOT: Path = Path('tests/data/markdown')


class MarkdownCase:
    """Class for markdown test case for a content-profile combination."""

    def __init__(
        self,
        test_id: str,
        markdown: str,
        profile_id: str,
        profile: Optional[Dict] = None,
        expected_output: Optional[str] = None,
    ) -> None:
        self.test_id: str = test_id
        self.markdown: str = markdown

        # self.profile_id is used to identify a MarkdownProfile class
        # stored in it's registry.
        self.profile_id: str = profile_id

        # self.profile will contain a custom class inherited from MarkdownProfile,
        # in the case of custom profiles specified in test cases, else None.
        self.profile: Optional[Type[MarkdownProfile]] = MarkdownCase.make_profile(
            profile, profile_id
        )
        self.expected_output: Optional[str] = expected_output

    @staticmethod
    def make_profile(profile: Optional[Dict], profile_id: str):
        if profile is None:
            return None

        class MarkdownProfileCustom(MarkdownProfile, name=profile_id):
            pass

        # Update self.args for the custom profile
        l: List = list(MarkdownProfileCustom.args)
        if 'args_config' in profile:
            l[0] = profile['args_config']
        if 'args_options' in profile:
            l[1].update(profile['args_options'])
        MarkdownProfileCustom.args = (l[0], l[1])

        # Update other keys, if present
        if 'plugins' in profile:
            MarkdownProfileCustom.plugins = profile['plugins']
        if 'post_config' in profile:
            MarkdownProfileCustom.post_config = profile['post_config']
        if 'render_with' in profile:
            MarkdownProfileCustom.render_with = profile['render_with']
        return MarkdownProfileCustom

    def __repr__(self) -> str:
        return self.case_id

    @property
    def case_id(self) -> str:
        return f'{self.test_id}-{self.profile_id}'

    @property
    def markdown_profile(self) -> Union[str, Type[MarkdownProfile]]:
        """
        Return the markdown profile for the test case.

        Output is str if the profile is pre-defined,
        else a custom class inherited from MarkdownProfile.
        """
        return self.profile if self.profile is not None else self.profile_id

    @property
    def output(self) -> str:
        return markdown(self.markdown, self.markdown_profile)

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
                # and store each test case in test_map[test_id][profile_id]
                cls.test_map[test_id] = {
                    profile_id: MarkdownCase(
                        test_id,
                        test_data['markdown'],
                        profile_id,
                        profile=profile,
                        expected_output=exp.get(profile_id, None),
                    )
                    for profile_id, profile in {
                        **{p: None for p in config.get('profiles', [])},
                        **config.get('custom_profiles', {}),
                    }.items()
                }

    @classmethod
    def dump(cls) -> None:
        if cls.test_map is not None:
            for test_id, data in cls.test_files.items():
                data['expected_output'] = {
                    profile_id: tomlkit.api.string(case.output, multiline=True)
                    for profile_id, case in cls.test_map[test_id].items()
                }
                (DATAROOT / test_id).write_text(tomlkit.dumps(data))

    @classmethod
    def test_cases(cls) -> List[Tuple[str, str]]:
        cls.load()
        return (
            [
                (test_id, profile_id)
                for test_id, test in cls.test_map.items()
                for profile_id in test.keys()
            ]
            if cls.test_map is not None
            else []
        )

    @classmethod
    def test_case(cls, test_id: str, profile_id: str) -> MarkdownCase:
        return cls.test_map[test_id][profile_id]  # type: ignore[index]

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
        for test_id, profile_id in cls.test_cases():
            case: MarkdownCase = cls.test_case(test_id, profile_id)
            op = copy(case_template)
            del op['id']
            op.select('.filename')[0].string = case.test_id
            op.select('.profile')[0].string = str(case.profile_id)
            op.select('.config')[0].string = ''
            op.select('.markdown .output')[0].append(case.markdown)
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
    assert markdown(None, MarkdownProfile) is None


def test_markdown_blank() -> None:
    blank_response = Markup('')
    assert markdown('', 'basic') == blank_response
    assert markdown('', 'document') == blank_response
    assert markdown('', 'inline') == blank_response
    assert markdown('', MarkdownProfile) == blank_response


@pytest.mark.parametrize(
    ('test_id', 'profile_id'),
    MarkdownTestRegistry.test_cases(),
)
# def test_markdown_cases(test_id: str, profile_id: str, unified_diff_output) -> None:
def test_markdown_cases(test_id: str, profile_id: str) -> None:
    case: MarkdownCase = MarkdownTestRegistry.test_case(test_id, profile_id)
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
