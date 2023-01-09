# mypy: disable-error-code=index
"""Tests for the mustache template escaper."""

import pytest

from funnel.utils.mustache import mustache_md

DATA = {
    'name': 'Unseen',
    'md_name': '**Unseen** University',
    'org': {
        'name': '`Unseen` University',
        'city': '~~Unknown~~Ankh-Morpork',
        'people': [
            {'first': 'Alberto', 'last': 'Malich', 'ceo': False},
            {'first': 'Mustrum', 'last': 'Ridcully', 'ceo': True},
            {'first': 'The', 'last': 'Librarian', 'ceo': False},
            {'first': 'Ponder', 'last': 'Stibbons', 'ceo': False},
        ],
        'vendors': [],
    },
}

ESCAPED_DATA = {
    'name': 'Unseen',
    'md_name': '\\*\\*Unseen\\*\\* University',
    'org': {
        'name': '\\`Unseen\\` University',
        'city': '\\~\\~Unknown\\~\\~Ankh\\-Morpork',
        'people': DATA['org']['people'],
        'vendors': [],
    },
}

TEMPLATES = {}
TEMPLATES['basic'] = (
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
- {{first}} {{last}}{{#ceo}} (CEO){{/ceo}}
{{/people}}{{! ignore me }}
### Vendors
{{^vendors}}
> No vendors
{{/vendors}}
{{/org}}
""",
    f"""
Name: {ESCAPED_DATA['name']}
**Bold Name**: {ESCAPED_DATA['md_name']}
Organization: { ESCAPED_DATA['org']['name'] }, { ESCAPED_DATA['org']['city'] }
## Organization Details
Name: { ESCAPED_DATA['org']['name'] }
City: { ESCAPED_DATA['org']['city'] }

### People
"""
    + '\n'.join(
        [
            f'- { p["first"] } { p["last"]}{" (CEO)" if p["ceo"] else ""}'
            for p in ESCAPED_DATA['org']['people']
        ]
    )
    + """

### Vendors
> No vendors
""",
)


@pytest.mark.parametrize(
    ('template', 'expected_output'), TEMPLATES.values(), ids=TEMPLATES.keys()
)
def test_mustache_md(template, expected_output):
    output = mustache_md(template, DATA)
    assert expected_output == output
