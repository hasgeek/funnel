"""Test configuration for markdown tests."""

from __future__ import annotations

from copy import copy
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest
import tomlkit
from bs4 import BeautifulSoup
from bs4.element import Tag
from markupsafe import Markup

if TYPE_CHECKING:
    from tomlkit.container import Container as TOMLContainer

    from funnel.utils.markdown import MarkdownConfig

md_tests_data_root = Path(__file__).parent / 'data'


class MarkdownCase:
    """Class for markdown test case for a content-profile combination."""

    def __init__(
        self,
        md_testname: str,
        mdtext: str,
        md_configname: str,
        config: dict | None = None,
        expected_output: str | None = None,
    ) -> None:
        from funnel.utils.markdown import MarkdownConfig  # pylint: disable=C0415

        self.md_testname = md_testname
        self.mdtext = mdtext
        self.md_configname = md_configname
        self.config = (
            MarkdownConfig(**config)
            if config is not None
            else MarkdownConfig.registry[md_configname]
        )
        self.expected_output = expected_output

    def __repr__(self) -> str:
        return self.caseid

    @property
    def caseid(self) -> str:
        return f'{self.md_testname}-{self.md_configname}'

    @property
    def markdown_config(self) -> str | MarkdownConfig:
        """
        Return the markdown config for the test case.

        Output is str if the config is pre-defined,
        else a custom class inherited from MarkdownConfig.
        """
        return self.config if self.config is not None else self.md_configname

    @property
    def output(self) -> str:
        return self.config.render(self.mdtext)

    def update_expected_output(self) -> None:
        self.expected_output = self.output


class MarkdownTestRegistry:
    test_map: ClassVar[dict[str, dict[str, MarkdownCase]] | None] = None
    test_files: ClassVar[dict[str, tomlkit.TOMLDocument]]

    @classmethod
    def load(cls) -> None:
        """Load test cases from .toml files and create a 2D map."""
        if cls.test_map is None:
            test_map = {}
            cls.test_files = {
                file.name: tomlkit.loads(file.read_text())
                for file in md_tests_data_root.iterdir()
                if file.suffix == '.toml'
            }
            for md_testname, test_data in cls.test_files.items():
                config = test_data['config']
                if TYPE_CHECKING:
                    assert isinstance(config, TOMLContainer)
                exp = test_data.get('expected_output', {})
                # Combine pre-defined profiles with custom profiles
                # and store each test case in test_map[md_testname][md_configname]
                test_map[md_testname] = {
                    md_configname: MarkdownCase(
                        md_testname=md_testname,
                        mdtext=test_data['markdown'],  # type: ignore[arg-type]
                        md_configname=md_configname,
                        config=config,
                        expected_output=(
                            None
                            if (output := exp.get(md_configname)) is None
                            else Markup(output)  # noqa: S704
                        ),
                    )
                    for md_configname, config in {
                        **dict.fromkeys(config.get('profiles', [])),
                        **config.get('custom_profiles', {}),
                    }.items()
                }
            cls.test_map = test_map

    @classmethod
    def dump(cls) -> None:
        # pylint: disable=unsubscriptable-object
        if cls.test_map is not None:
            for md_testname, data in cls.test_files.items():
                data['expected_output'] = {
                    md_configname: tomlkit.string(case.output, multiline=True)
                    for md_configname, case in cls.test_map[md_testname].items()
                }
                (md_tests_data_root / md_testname).write_text(tomlkit.dumps(data))

    @classmethod
    def test_cases(cls) -> list[tuple[str, str]]:
        cls.load()
        return (
            [
                (md_testname, md_configname)
                for md_testname, test in cls.test_map.items()
                for md_configname in test
            ]
            if cls.test_map is not None
            else []
        )

    @classmethod
    def test_case(cls, md_testname: str, md_configname: str) -> MarkdownCase:
        # pylint: disable=unsubscriptable-object
        return cls.test_map[md_testname][md_configname]  # type: ignore[index]

    @classmethod
    def update_expected_output(cls) -> None:
        cls.load()
        cls.dump()

    @classmethod
    def update_debug_output(cls) -> None:
        """Save test output in file output.html for visual debugging."""
        cls.load()
        template = BeautifulSoup(
            (md_tests_data_root / 'template.html').read_text(), 'html.parser'
        )
        case_template = template.find(id='output_template')
        assert isinstance(case_template, Tag)
        for md_testname, md_configname in cls.test_cases():
            case: MarkdownCase = cls.test_case(md_testname, md_configname)
            op = copy(case_template)
            del op['id']
            op.select('.filename')[0].string = case.md_testname
            op.select('.profile')[0].string = str(case.md_configname)
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
            existing_class = op.get('class')
            if not existing_class:
                existing_class = []
            elif isinstance(existing_class, str):
                existing_class = [existing_class]
            op['class'] = [
                *existing_class,
                'success' if case.expected_output == case.output else 'failed',
            ]
            body = template.find('body')
            assert isinstance(body, Tag)
            body.append(op)
        generated = template.find(id='generated')
        assert isinstance(generated, Tag)
        generated.string = datetime.now().strftime('%d %B, %Y %H:%M:%S')
        (md_tests_data_root / 'output.html').write_text(template.prettify())


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if (
        'md_testname' in metafunc.fixturenames
        and 'md_configname' in metafunc.fixturenames
    ):
        metafunc.parametrize(
            ('md_testname', 'md_configname'), MarkdownTestRegistry.test_cases()
        )

    if 'markdown_test_registry' in metafunc.fixturenames:
        metafunc.parametrize('markdown_test_registry', [MarkdownTestRegistry])
