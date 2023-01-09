# mypy: disable-error-code=index
"""Tests for the mustache template escaper."""

import pytest

from funnel.utils.mustache import mustache_md

test_data = {
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

escaped_data = {
    'name': 'Unseen',
    'md_name': '\\*\\*Unseen\\*\\* University',
    'org': {
        'name': '\\`Unseen\\` University',
        'city': '\\~\\~Unknown\\~\\~Ankh\\-Morpork',
        'people': test_data['org']['people'],
        'vendors': [],
    },
}

templates = {}
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
- {{first}} {{last}}{{#ceo}} (CEO){{/ceo}}
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
"""
    + '\n'.join(
        [
            f'- { p["first"] } { p["last"]}{" (CEO)" if p["ceo"] else ""}'
            for p in escaped_data['org']['people']
        ]
    )
    + """

### Vendors
> No vendors
""",
)


@pytest.mark.parametrize(
    ('template', 'expected_output'), templates.values(), ids=templates.keys()
)
def test_mustache_md(template, expected_output):
    output = mustache_md(template, test_data)
    assert expected_output == output
