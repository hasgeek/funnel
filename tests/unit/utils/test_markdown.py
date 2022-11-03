"""Tests for markdown parser."""

from pathlib import Path
from typing import Dict, List, Optional, Type
import warnings

import pytest
import tomlkit

from funnel.utils.markdown import markdown
from funnel.utils.markdown.profiles import MarkdownProfile, profiles

DATAROOT: Path = Path('tests/data/markdown')
DEBUG = True


class MarkdownCase:
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
        self.profile_id: str = profile_id
        self.profile: Optional[Type[MarkdownProfile]] = MarkdownCase.make_profile(
            profile
        )
        self.expected_output: Optional[str] = expected_output

        if self.is_custom() and self.profile_id in profiles:
            raise Exception(
                f'Case {self.case_id}: Custom profiles cannot use a key that is pre-defined in profiles'
            )

    @staticmethod
    def make_profile(profile: Optional[Dict]):
        if profile is None:
            return None

        class MarkdownProfileCustom(MarkdownProfile):
            pass

        l: List = list(MarkdownProfileCustom.args)
        if 'args_config' in profile:
            l[0] = profile['args_config']
        if 'args_options' in profile:
            l[1].update(profile['args_options'])
        MarkdownProfileCustom.args = (l[0], l[1])
        if 'plugins' in profile:
            MarkdownProfileCustom.plugins = profile['plugins']
        if 'post_config' in profile:
            MarkdownProfileCustom.post_config = profile['post_config']
        if 'render_with' in profile:
            MarkdownProfileCustom.render_with = profile['render_with']
        return MarkdownProfileCustom

    def __repr__(self) -> str:
        return self.case_id

    def is_custom(self):
        return self.profile is not None

    @property
    def case_id(self) -> str:
        return f'{self.test_id}-{self.profile_id}'

    @property
    def markdown_profile(self):
        return self.profile if self.profile is not None else self.profile_id

    @property
    def output(self):
        return (
            markdown(self.markdown, self.markdown_profile)
            .__str__()
            .lstrip('\n\r')
            .rstrip(' \n\r')
        )


class MarkdownTestRegistry:
    test_map: Optional[Dict[str, Dict[str, MarkdownCase]]] = None

    @classmethod
    def load(cls):
        if cls.test_map is None:
            cls.test_map = {}
            tests = {
                file.name: tomlkit.loads(file.read_text())
                for file in DATAROOT.iterdir()
                if file.suffix == '.toml'
            }
            for test_id, test in tests.items():
                config = test['config']
                exp = test.get('expected_output', {})
                cls.test_map[test_id] = {
                    profile_id: MarkdownCase(
                        test_id,
                        test['markdown'],
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
    def dataset(cls) -> List[MarkdownCase]:
        cls.load()
        return (
            [case for tests in cls.test_map.values() for case in tests.values()]
            if cls.test_map is not None
            else []
        )


@pytest.mark.parametrize(
    'case',
    MarkdownTestRegistry.dataset(),
)
def test_markdown_cases(case: MarkdownCase, unified_diff_output) -> None:
    if case.expected_output is None:
        warnings.warn(f'Expected output not generated for {case}')
        pytest.skip(f'Expected output not generated for {case}')

    if DEBUG:
        unified_diff_output(case.expected_output, case.output)
    else:
        assert case.expected_output == case.output
