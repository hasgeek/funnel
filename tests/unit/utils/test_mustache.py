# mypy: disable-error-code=index
"""Tests for the mustache template escaper."""

import pytest

from funnel.utils.mustache import mustache_md

DATA = {
    'name': 'Hasgeek',
    'md_name': '**Hasgeek** Learning Pvt. Ltd.',
    'org': {
        'name': '`Hasgeek` Learning Pvt. Ltd.',
        'city': '~~Bangalore~~Bengaluru',
        'people': [
            {'first': 'Zainab', 'last': 'Bawa', 'ceo': False},
            {'first': 'Kiran', 'last': 'Jonnalagadda', 'ceo': True},
        ],
        'vendors': [],
    },
}

ESCAPED_DATA = {
    'name': 'Hasgeek',
    'md_name': '\\*\\*Hasgeek\\*\\* Learning Pvt\\. Ltd\\.',
    'org': {
        'name': '\\`Hasgeek\\` Learning Pvt\\. Ltd\\.',
        'city': '\\~\\~Bangalore\\~\\~Bengaluru',
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
