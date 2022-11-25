"""Markdown preview view."""


from typing import Optional

from flask import request

from ... import app
from ...typing import ReturnView
from ...utils import markdown
from ...utils.markdown.profiles import profiles


@app.route('/api/1/preview/markdown', methods=['POST'])
def markdown_preview() -> ReturnView:
    """Render Markdown in the backend, with custom options based on use case."""
    profile: Optional[str] = request.form.get('profile')
    if profile is None or profile not in profiles:
        return {
            'status': 'error',
            'error': 'not_implemented',
            'error_description': f'Markdown profile {profile} is not supported',
        }, 501
    text = request.form.get('text')

    html = markdown(text, profile)

    return {
        'status': 'ok',
        'profile': profile,
        'html': html,
    }
