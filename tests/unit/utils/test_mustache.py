# mypy: disable-error-code=index
"""Tests for the mustache template escaper."""

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

escaped_data = {
    'name': 'Unseen',
    'md_name': '\\*\\*Unseen\\*\\* University',
    'org': {
        'name': '\\`Unseen\\` University',
        'city': '\\~\\~Unknown\\~\\~Ankh\\-Morpork',
        'people': test_data['org']['people'],
        'vendors': [],
    },
    'punctuations': (
        '\\!\\"\\#\\$\\%\\&\\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@'
        + '\\[\\\\\\]\\^\\_\\`\\{\\|\\}\\~'
    ),
    'escaped-sequence': '\\\\→\\\\A\\\\a\\\\ \\\\3\\\\φ\\\\«',
}

templates = {}
markdown_output = {}

templates['basic'] = (
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
    f"""
Name: {escaped_data['name']}
**Bold Name**: {escaped_data['md_name']}
Organization: { escaped_data['org']['name'] }, { escaped_data['org']['city'] }
## Organization Details
Name: { escaped_data['org']['name'] }
City: { escaped_data['org']['city'] }

### People
- Alberto Malich
- Mustrum Ridcully (Archchancellor)
- The Librarian
- Ponder Stibbons

### Vendors
> No vendors
""",
)

templates['punctuations'] = (  # type: ignore[assignment]
    '{{ punctuations }}',
    escaped_data['punctuations'],
)

templates['escaped-sequence'] = (  # type: ignore[assignment]
    '{{ escaped-sequence }}',
    escaped_data['escaped-sequence'],
)


@pytest.mark.parametrize(
    ('template', 'expected_output'), templates.values(), ids=templates.keys()
)
def test_mustache_md(template, expected_output):
    output = mustache_md(template, test_data)
    assert expected_output == output


markdown_output['basic-basic'] = (
    templates['basic'][0],
    'basic',
    f"""<p>Name: {test_data['name']}<br />
<strong>Bold Name</strong>: {test_data['md_name']}<br />
Organization: { test_data['org']['name'] }, { test_data['org']['city'] }</p>
<h2>Organization Details</h2>
<p>Name: { test_data['org']['name'] }<br />
City: { test_data['org']['city'] }</p>
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
markdown_output['basic-document'] = (
    templates['basic'][0],
    'document',
    f"""<p>Name: {test_data['name']}<br />
<strong>Bold Name</strong>: {test_data['md_name']}<br />
Organization: { test_data['org']['name'] }, { test_data['org']['city'] }</p>
<h2 id="h:organization-details">Organization Details <a class="header-anchor" href="#h:organization-details">#</a></h2>
<p>Name: { test_data['org']['name'] }<br />
City: { test_data['org']['city'] }</p>
<h3 id="h:people">People <a class="header-anchor" href="#h:people">#</a></h3>
<ul>
<li>Alberto Malich</li>
<li>Mustrum Ridcully (Archchancellor)</li>
<li>The Librarian</li>
<li>Ponder Stibbons</li>
</ul>
<h3 id="h:vendors">Vendors <a class="header-anchor" href="#h:vendors">#</a></h3>
<blockquote>
<p>No vendors</p>
</blockquote>
""",
)

markdown_output['punctuations-inline'] = (
    templates['punctuations'][0],
    'inline',
    '!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~',
)
markdown_output['punctuations-basic'] = (
    templates['punctuations'][0],
    'basic',
    '<p>!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~</p>\n',
)
markdown_output['punctuations-document'] = (
    templates['punctuations'][0],
    'document',
    '<p>!&quot;#$%&amp;\'()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~</p>\n',
)

markdown_output['escaped-sequence-inline'] = (
    templates['escaped-sequence'][0],
    'inline',
    '\\→\\A\\a\\ \\3\\φ\\«',
)
markdown_output['escaped-sequence-basic'] = (
    templates['escaped-sequence'][0],
    'basic',
    '<p>\\→\\A\\a\\ \\3\\φ\\«</p>\n',
)
markdown_output['escaped-sequence-document'] = (
    templates['escaped-sequence'][0],
    'document',
    '<p>\\→\\A\\a\\ \\3\\φ\\«</p>\n',
)


@pytest.mark.parametrize(
    ('template', 'profile', 'expected_output'),
    markdown_output.values(),
    ids=markdown_output.keys(),
)
def test_mustache_md_markdown(template, profile, expected_output):
    output = MarkdownConfig.registry[profile].render(mustache_md(template, test_data))
    assert expected_output == output
