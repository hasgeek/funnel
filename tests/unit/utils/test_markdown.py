"""Tests for markdown parser."""

from copy import copy, deepcopy
from datetime import datetime
from difflib import context_diff
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
import json
import os

from bs4 import BeautifulSoup
from markupsafe import Markup
import pytest
import tomlkit

from funnel.utils import markdown
from funnel.utils.markdown.helpers import MD_CONFIGS

DATA_ROOT = os.path.abspath(os.path.join('tests', 'data', 'markdown'))

CaseType = Dict[str, Any]
CasesType = Dict[str, CaseType]


@lru_cache()
def load_md_cases() -> CasesType:
    """Load test cases for the markdown parser from .toml files."""
    cases: CasesType = {}
    files = os.listdir(DATA_ROOT)
    files.sort()
    for file in files:
        if file.endswith('.toml'):
            with open(os.path.join(DATA_ROOT, file), encoding='utf-8') as f:
                cases[file] = tomlkit.load(f)
                f.close()
    return cases


def blank_to_none(_id: str):
    """Replace blank string with None."""
    return None if _id == "" else _id


def none_to_blank(_id: Optional[str]):
    """Replace None with a blank string."""
    return "" if _id is None else str(_id)


def get_case_configs(case: CaseType) -> Dict[str, Any]:
    """Return dict with key-value of configs for the provided test case."""
    case_configs: Dict[str, Any] = {}
    configs = copy(case['config']['configs'])
    md_configs = deepcopy(MD_CONFIGS)
    if 'extra_configs' in case['config']:
        for c in case['config']['extra_configs']:
            if c not in md_configs:
                md_configs[c] = case['config']['extra_configs'][c]
            if c not in configs:
                configs.append(c)
    for c in configs:
        c = blank_to_none(c)
        if c in md_configs:
            case_configs[c] = md_configs[c]
        else:
            case_configs[c] = None
    return case_configs


def get_md(case: CaseType, config: Optional[Dict[str, Any]]):
    """Parse a markdown test case for given configuration."""
    if config is None:
        return markdown("This configuration does not exist in `MD_CONFIG`.").__str__()
    return (
        markdown(  # pylint: disable=unnecessary-dunder-call
            case['data']['markdown'], **config
        )
        .__str__()
        .lstrip('\n\r')
        .rstrip(' \n\r')
    )


def update_md_case_results(cases: CasesType) -> None:
    """Update cases object with expected result for each case-config combination."""
    for case_id in cases:
        case = cases[case_id]
        configs = get_case_configs(case)
        case['expected_output'] = {}
        for config_id, config in configs.items():
            case['expected_output'][none_to_blank(config_id)] = get_md(case, config)


def dump_md_cases(cases: CasesType) -> None:
    """Save test cases for the markdown parser to .toml files."""
    for (file, file_data) in cases.items():
        with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f:
            tomlkit.dump(file_data, f)
            f.close()


def update_test_data() -> None:
    """Update test data after changes made to test cases and/or configurations."""
    cases = load_md_cases()
    update_md_case_results(cases)
    dump_md_cases(cases)


@lru_cache()
def get_output_template() -> BeautifulSoup:
    """Get bs4 output template for output.html for markdown tests."""
    with open(os.path.join(DATA_ROOT, 'template.html'), encoding='utf-8') as f:
        template = BeautifulSoup(f, 'html.parser')
        f.close()
        return template


@lru_cache()
def get_case_template() -> BeautifulSoup:
    """Get blank bs4 template for each case to be used to update test output."""
    return get_output_template().find(id='output_template')


# pylint: disable=too-many-arguments
def update_case_output(
    template: BeautifulSoup,
    case_id: str,
    case: CaseType,
    config_id: str,
    config: Dict[str, Any],
    output: str,
) -> None:
    """Update & return case template with output for provided case-configuration."""
    if 'output' not in case:
        case['output'] = {}
    case['output'][none_to_blank(config_id)] = output
    op = copy(get_case_template())
    del op['id']
    op.select('.filename')[0].string = case_id
    op.select('.configname')[0].string = str(config_id)
    op.select('.config')[0].string = json.dumps(config, indent=2)
    op.select('.markdown .output')[0].append(case['data']['markdown'])
    try:
        expected_output = case['expected_output'][none_to_blank(config_id)]
    except KeyError:
        expected_output = markdown(
            f'Expected output for `{case_id}` config `{config_id}` '
            'has not been generated. Please run `make tests-data-md`'
            '**after evaluating other failures**.\n'
            '`make tests-data-md` should only be run for this after '
            'ensuring there are no unexpected mismatches/failures '
            'in the output of all cases.\n'
            'For detailed instructions check the [readme](readme.md).'
        )
    op.select('.expected .output')[0].append(
        BeautifulSoup(expected_output, 'html.parser')
    )
    op.select('.final_output .output')[0].append(BeautifulSoup(output, 'html.parser'))
    op['class'] = op.get('class', []) + [
        'success' if expected_output == output and config is not None else 'failed'
    ]
    template.find('body').append(op)


def dump_md_output(output: BeautifulSoup) -> None:
    """Save test output in output.html."""
    output.find(id='generated').string = datetime.now().strftime('%d %B, %Y %H:%M:%S')
    with open(os.path.join(DATA_ROOT, 'output.html'), 'w', encoding='utf-8') as f:
        f.write(output.prettify())


@lru_cache()
def get_md_test_data() -> CasesType:
    """Get cases updated with final output alongwith test cases dataset."""
    template = get_output_template()
    cases = load_md_cases()
    for case_id, case in cases.items():
        configs = get_case_configs(case)
        for config_id, config in configs.items():
            test_output = get_md(case, config)
            update_case_output(
                template,
                case_id,
                case,
                config_id,
                config,
                test_output,
            )
    dump_md_output(template)
    return cases


def get_md_test_dataset() -> List[Tuple[str, str]]:
    """Return testcase datasets."""
    return [
        (case_id, none_to_blank(config_id))
        for (case_id, case) in load_md_cases().items()
        for config_id in get_case_configs(case)
    ]


def get_md_test_output(case_id: str, config_id: str) -> Tuple[str, str]:
    """Return expected output and final output for quoted case-config combination."""
    cases = get_md_test_data()
    try:
        return (
            cases[case_id]['expected_output'][none_to_blank(config_id)],
            cases[case_id]['output'][none_to_blank(config_id)],
        )
    except KeyError:
        return (
            f'Expected output for "{case_id}" config "{config_id}" has not been generated. '
            'Please run "make tests-data-md" '
            'after evaluating other failures.\n'
            '"make tests-data-md" should only be run for this after '
            'ensuring there are no unexpected mismatches/failures '
            'in the output of all cases.\n',
            'For detailed instructions check "tests/data/markdown/readme.md". \n'
            + (
                cases[case_id]['output'][none_to_blank(config_id)]
                if len(cases[case_id]['output'][none_to_blank(config_id)]) <= 160
                else '\n'.join(
                    [
                        cases[case_id]['output'][none_to_blank(config_id)][:80],
                        '...',
                        cases[case_id]['output'][none_to_blank(config_id)][-80:],
                    ]
                )
            ),
        )


def test_markdown_none() -> None:
    assert markdown(None) is None


def test_markdown_blank() -> None:
    assert markdown('') == Markup('')


@pytest.mark.update_markdown_data()
def test_markdown_update_output(pytestconfig):
    has_mark = pytestconfig.getoption('-m', default=None) == 'update_markdown_data'
    if not has_mark:
        pytest.skip('Skipping update of expected output of markdown test cases')
    update_test_data()


@pytest.mark.parametrize(
    (
        'case_id',
        'config_id',
    ),
    get_md_test_dataset(),
)
def test_markdown_dataset(case_id: str, config_id: str) -> None:
    (expected_output, output) = get_md_test_output(case_id, config_id)
    cases = load_md_cases()
    configs = get_case_configs(cases[case_id])
    if configs[blank_to_none(config_id)] is None or expected_output != output:
        if configs[blank_to_none(config_id)] is None:
            msg = [output]
        else:
            difference = context_diff(expected_output.split('\n'), output.split('\n'))
            msg = []
            for line in difference:
                if not line.startswith(' '):
                    msg.append(line)
        pytest.fail(
            '\n'.join(
                [
                    f'Markdown output failed. File: {case_id}, Config key: {config_id}.',
                    'Please check tests/data/markdown/output.html for detailed output comparision',
                ]
                + msg
            ),
            pytrace=False,
        )
