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
from funnel.utils.markdown.profiles import default_markdown_options, profiles

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


def get_case_profiles(case: CaseType) -> Dict[str, Any]:
    """Return dict with key-value of profiles for the provided test case."""
    profiles_out: Dict[str, Any] = {}
    case_profiles = copy(case['config']['profiles'])
    _profiles = deepcopy(profiles)
    if 'custom_profiles' in case['config']:
        for p in case['config']['custom_profiles']:
            if p not in _profiles:
                _profiles[p] = case['config']['custom_profiles'][p]
                if _profiles[p]['args_options_update'] is False:
                    _profiles[p]['args_options_update'] = default_markdown_options
                _profiles[p]['args'] = (
                    _profiles[p]['args_config'],
                    _profiles[p]['args_options_update'],
                )
            if p not in case_profiles:
                case_profiles.append(p)
    for p in case_profiles:
        if p in _profiles:
            profiles_out[p] = _profiles[p]
        else:
            profiles_out[p] = None
    return profiles_out


def get_md(case: CaseType, profile: Optional[Dict[str, Any]]):
    """Parse a markdown test case for given configuration profile."""
    if profile is None:
        return markdown(
            'This configuration profile has not been specified.', 'basic'
        ).__str__()
    return (
        markdown(  # pylint: disable=unnecessary-dunder-call
            case['data']['markdown'], profile
        )
        .__str__()
        .lstrip('\n\r')
        .rstrip(' \n\r')
    )


def update_expected_case_output(cases: CasesType) -> None:
    """Update cases object with expected output for each case-profile combination."""
    for case_id in cases:
        case = cases[case_id]
        _profiles = get_case_profiles(case)
        case['expected_output'] = {}
        for profile_id, _profile in _profiles.items():
            case['expected_output'][profile_id] = get_md(
                case, profiles[profile_id] if profile_id in profiles else _profile
            )


def dump_md_cases(cases: CasesType) -> None:
    """Save test cases for the markdown parser to .toml files."""
    for (file, file_data) in cases.items():
        with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f:
            tomlkit.dump(file_data, f)
            f.close()


def update_test_data() -> None:
    """Update test data after changes made to test cases and/or configurations."""
    cases = load_md_cases()
    update_expected_case_output(cases)
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
    profile_id: str,
    profile: Dict[str, Any],
    output: str,
) -> None:
    """Update & return case template with output for provided case-configuration."""
    profile = deepcopy(profile)
    if 'output' not in case:
        case['output'] = {}
    case['output'][profile_id] = output
    op = copy(get_case_template())
    del op['id']
    op.select('.filename')[0].string = case_id
    op.select('.profile')[0].string = str(profile_id)
    if 'args_config' in profile:
        del profile['args_config']
    if 'args_options_update' in profile:
        del profile['args_options_update']
    op.select('.config')[0].string = json.dumps(profile, indent=2)
    op.select('.markdown .output')[0].append(case['data']['markdown'])
    try:
        expected_output = case['expected_output'][profile_id]
    except KeyError:
        expected_output = markdown(
            f'Expected output for `{case_id}` config `{profile_id}` '
            'has not been generated. Please run `make tests-data-md`'
            '**after evaluating other failures**.\n'
            '`make tests-data-md` should only be run for this after '
            'ensuring there are no unexpected mismatches/failures '
            'in the output of all cases.\n'
            'For detailed instructions check the [readme](readme.md).',
            'basic',
        )
    op.select('.expected .output')[0].append(
        BeautifulSoup(expected_output, 'html.parser')
    )
    op.select('.final_output .output')[0].append(BeautifulSoup(output, 'html.parser'))
    op['class'] = op.get('class', []) + [
        'success' if expected_output == output and profile is not None else 'failed'
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
        _profiles = get_case_profiles(case)
        for profile_id, profile in _profiles.items():
            test_output = get_md(case, profile)
            update_case_output(
                template,
                case_id,
                case,
                profile_id,
                profile,
                test_output,
            )
    dump_md_output(template)
    return cases


def get_md_test_dataset() -> List[Tuple[str, str]]:
    """Return testcase datasets."""
    return [
        (case_id, profile_id)
        for (case_id, case) in load_md_cases().items()
        for profile_id in get_case_profiles(case)
    ]


def get_md_test_output(case_id: str, profile_id: str) -> Tuple[str, str]:
    """Return expected output and final output for quoted case-config combination."""
    cases = get_md_test_data()
    try:
        return (
            cases[case_id]['expected_output'][profile_id],
            cases[case_id]['output'][profile_id],
        )
    except KeyError:
        return (
            f'Expected output for "{case_id}" config "{profile_id}" has not been generated. '
            'Please run "make tests-data-md" '
            'after evaluating other failures.\n'
            '"make tests-data-md" should only be run for this after '
            'ensuring there are no unexpected mismatches/failures '
            'in the output of all cases.\n',
            'For detailed instructions check "tests/data/markdown/readme.md". \n'
            + (
                cases[case_id]['output'][profile_id]
                if len(cases[case_id]['output'][profile_id]) <= 160
                else '\n'.join(
                    [
                        cases[case_id]['output'][profile_id][:80],
                        '...',
                        cases[case_id]['output'][profile_id][-80:],
                    ]
                )
            ),
        )


def test_markdown_none() -> None:
    assert markdown(None, 'basic') is None
    assert markdown(None, 'document') is None


def test_markdown_blank() -> None:
    assert markdown('', 'basic') == Markup('')
    assert markdown('', 'document') == Markup('')


@pytest.mark.update_markdown_data()
def test_markdown_update_output(pytestconfig):
    has_mark = pytestconfig.getoption('-m', default=None) == 'update_markdown_data'
    if not has_mark:
        pytest.skip('Skipping update of expected output of markdown test cases')
    update_test_data()


@pytest.mark.parametrize(
    (
        'case_id',
        'profile_id',
    ),
    get_md_test_dataset(),
)
def test_markdown_dataset(case_id: str, profile_id: str) -> None:
    (expected_output, output) = get_md_test_output(case_id, profile_id)
    cases = load_md_cases()
    _profiles = get_case_profiles(cases[case_id])
    if _profiles[profile_id] is None or expected_output != output:
        if _profiles[profile_id] is None:
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
                    f'Markdown output failed. File: {case_id}, Config key: {profile_id}.',
                    'Please check tests/data/markdown/output.html for detailed output comparision',
                ]
                + msg
            ),
            pytrace=False,
        )
