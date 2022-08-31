"""Helpers for markdown parser tests."""

from copy import copy, deepcopy
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Tuple
import json
import os

from bs4 import BeautifulSoup
import toml

from funnel.utils.markdown.base import markdown
from funnel.utils.markdown.helpers import MD_CONFIGS

DATA_ROOT = os.path.abspath(os.path.join('tests', 'data', 'markdown'))

CaseType = Dict[str, Any]
CasesType = Dict[str, CaseType]


def load_md_cases() -> CasesType:
    cases: CasesType = {}
    for file in os.listdir(DATA_ROOT):
        if file.endswith('.toml'):
            with open(os.path.join(DATA_ROOT, file), encoding='utf-8') as f:
                cases[file] = toml.load(f)
                f.close()
    return cases


def get_case_configs(case: CaseType) -> Dict[str, Any]:
    case_configs = {}
    configs = copy(case['config']['configs'])
    md_configs = deepcopy(MD_CONFIGS)
    if 'extra_configs' in case['config']:
        if 'extra_configs' in case['config']:
            for c in case['config']['extra_configs']:
                if c not in md_configs:
                    md_configs[c] = case['config']['extra_configs'][c]
                if c not in configs:
                    configs.append(c)
    for c in configs:
        if c in md_configs:
            case_configs[c] = md_configs[c]
    return case_configs


def get_md(case: CaseType, config: Dict[str, Any]):
    return (
        markdown(  # pylint: disable=unnecessary-dunder-call
            case['data']['markdown'], **config
        )
        .__str__()
        .lstrip('\n\r')
        .rstrip(' \n\r')
    )


def update_md_case_results(cases: CasesType) -> None:
    for case_id in cases:
        case = cases[case_id]

        configs = get_case_configs(case)
        for config_id, config in configs.items():
            case['results'][config_id] = get_md(case, config)


def dump_md_cases(cases: CasesType) -> None:
    for (file, file_data) in cases.items():
        with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f:
            toml.dump(file_data, f)
            f.close()


def update_test_data() -> None:
    cases = load_md_cases()
    update_md_case_results(cases)
    dump_md_cases(cases)


@lru_cache()
def get_output_template() -> BeautifulSoup:
    with open(os.path.join(DATA_ROOT, 'template.html'), encoding='utf-8') as f:
        template = BeautifulSoup(f, 'html.parser')
        f.close()
        return template


@lru_cache()
def get_case_template() -> BeautifulSoup:
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
    op = copy(get_case_template())
    del op['id']
    op.select('.filename')[0].string = case_id
    op.select('.configname')[0].string = config_id
    op.select('.config')[0].string = json.dumps(config, indent=2)
    op.select('.markdown .output')[0].append(case['data']['markdown'])
    expected_output = case['results'][config_id]
    op.select('.expected .output')[0].append(
        BeautifulSoup(case['results'][config_id], 'html.parser')
    )
    op.select('.final_output .output')[0].append(BeautifulSoup(output, 'html.parser'))
    op['class'] = op.get('class', []) + [
        'success' if expected_output == output else 'failed'
    ]
    template.find('body').append(op)


def dump_md_output(output: BeautifulSoup) -> None:
    output.find(id='generated').string = datetime.now().strftime('%d %B, %Y %H:%M:%S')
    with open(os.path.join(DATA_ROOT, 'output.html'), 'w', encoding='utf-8') as f:
        f.write(output.prettify())


def md_output_exists() -> bool:
    return os.path.exists(os.path.join(DATA_ROOT, 'output.html'))


def get_md_test_data():
    template = get_output_template()
    cases = load_md_cases()
    dataset: List[Tuple[str, str]] = []
    for case_id, case in cases.items():
        configs = get_case_configs(case)
        for config_id, config in configs.items():
            expected_output = case['results'][config_id]
            test_output = get_md(case, config)
            update_case_output(
                template,
                case_id,
                case,
                config_id,
                config,
                test_output,
            )
            dataset.append((expected_output, test_output))
    dump_md_output(template)
    return dataset
