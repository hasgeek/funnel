# mypy: disable-error-code=index
"""Tests for the mustache template escaper."""

from typing import Dict, Tuple

import pytest

from funnel.utils.markdown.base import MarkdownConfig
from funnel.utils.mustache import mustache_md

test_data = {
    'name': 'Unseen',
    'md_name': '**Unseen** University',
    'org': {
        'name': '`Unseen` University',
        'city': '~~Unknown~~Ankh-Morpork',
        'people': [
            {'first': 'Alberto', 'last': 'Malich', 'archchancellor': False},
            {'first': 'Mustrum', 'last': 'Ridcully', 'archchancellor': True},
            {'first': 'The', 'last': 'Librarian', 'archchancellor': False},
            {'first': 'Ponder', 'last': 'Stibbons', 'archchancellor': False},
        ],
        'vendors': [],
    },
    'punctuations': '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~',
    'escaped-sequence': '\\→\\A\\a\\ \\3\\φ\\«',
}

#: Dict of {test_name: (template, output)}
templates_and_output: Dict[str, Tuple[str, str]] = {}
config_template_output: Dict[str, Tuple[str, str, str]] = {}

templates_and_output['basic'] = (
    """
Name: {{name}}
**Bold Name**: {{ md_name }}
Organization: {{org.name }}, {{ org.city}}
{{#org}}
## Organization Details
Name: {{name}}
City: {{city}}

### People
{{#people}}
- {{first}} {{last}}{{#archchancellor}} (Archchancellor){{/archchancellor}}
{{/people}}{{! ignore me }}
### Vendors
{{^vendors}}
> No vendors
{{/vendors}}
{{/org}}
""",
    """
Name: Unseen
**Bold Name**: \\*\\*Unseen\\*\\* University
Organization: \\`Unseen\\` University, \\~\\~Unknown\\~\\~Ankh\\-Morpork
## Organization Details
Name: \\`Unseen\\` University
City: \\~\\~Unknown\\~\\~Ankh\\-Morpork

### People
- Alberto Malich
- Mustrum Ridcully (Archchancellor)
- The Librarian
- Ponder Stibbons

### Vendors
> No vendors
""",
)

templates_and_output['punctuations'] = (
    '{{ punctuations }}',
    '\\!\\"\\#\\$\\%\\&\\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@'
    '\\[\\\\\\]\\^\\_\\`\\{\\|\\}\\~',
)

templates_and_output['escaped-sequence'] = (
    '{{ escaped-sequence }}',
    '\\\\→\\\\A\\\\a\\\\ \\\\3\\\\φ\\\\«',
)


@pytest.mark.parametrize(
    ('template', 'expected_output'),
    templates_and_output.values(),
    ids=templates_and_output.keys(),
)
def test_mustache_md(template, expected_output):
    output = mustache_md(template, test_data)  # pylint: disable=not-callable
    assert expected_output == output


config_template_output['basic-basic'] = (
    'basic',
    templates_and_output['basic'][0],
    """<p>Name: Unseen<br />
<strong>Bold Name</strong>: **Unseen** University<br />
Organization: `Unseen` University, ~~Unknown~~Ankh-Morpork</p>
<h2>Organization Details</h2>
<p>Name: `Unseen` University<br />
City: ~~Unknown~~Ankh-Morpork</p>
<h3>People</h3>
<ul>
<li>Alberto Malich</li>
<li>Mustrum Ridcully (Archchancellor)</li>
<li>The Librarian</li>
<li>Ponder Stibbons</li>
</ul>
<h3>Vendors</h3>
<blockquote>
<p>No vendors</p>
</blockquote>
""",
)
config_template_output['basic-document'] = (
    'document',
    templates_and_output['basic'][0],
    """<p>Name: Unseen<br />
<strong>Bold Name</strong>: **Unseen** University<br />
Organization: `Unseen` University, ~~Unknown~~Ankh-Morpork</p>
<h2 id="h:organization-details"><a href="#h:organization-details">Organization Details</a></h2>
<p>Name: `Unseen` University<br />
City: ~~Unknown~~Ankh-Morpork</p>
<h3 id="h:people"><a href="#h:people">People</a></h3>
<ul>
<li>Alberto Malich</li>
<li>Mustrum Ridcully (Archchancellor)</li>
<li>The Librarian</li>
<li>Ponder Stibbons</li>
</ul>
<h3 id="h:vendors"><a href="#h:vendors">Vendors</a></h3>
<blockquote>
<p>No vendors</p>
</blockquote>
""",
)

config_template_output['punctuations-inline'] = (
    'inline',
    templates_and_output['punctuations'][0],
    '!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~',
)
config_template_output['punctuations-basic'] = (
    'basic',
    templates_and_output['punctuations'][0],
    '<p>!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~</p>\n',
)
config_template_output['punctuations-document'] = (
    'document',
    templates_and_output['punctuations'][0],
    '<p>!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~</p>\n',
)

config_template_output['escaped-sequence-inline'] = (
    'inline',
    templates_and_output['escaped-sequence'][0],
    '\\→\\A\\a\\ \\3\\φ\\«',
)
config_template_output['escaped-sequence-basic'] = (
    'basic',
    templates_and_output['escaped-sequence'][0],
    '<p>\\→\\A\\a\\ \\3\\φ\\«</p>\n',
)
config_template_output['escaped-sequence-document'] = (
    'document',
    templates_and_output['escaped-sequence'][0],
    '<p>\\→\\A\\a\\ \\3\\φ\\«</p>\n',
)


@pytest.mark.parametrize(
    ('config', 'template', 'expected_output'),
    config_template_output.values(),
    ids=config_template_output.keys(),
)
def test_mustache_md_markdown(template, config, expected_output):
    assert expected_output == MarkdownConfig.registry[config].render(
        mustache_md(template, test_data)  # pylint: disable=not-callable
    )
