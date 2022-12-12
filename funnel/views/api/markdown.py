"""Markdown preview view."""


from typing import Optional

from flask import request

from baseframe import _

from ... import app
from ...typing import ReturnView
from ...utils import MarkdownConfig


# TODO: Require login and add rate limit (but how?)
@app.route('/api/1/preview/markdown', methods=['POST'])
def markdown_preview() -> ReturnView:
    """Render Markdown in the backend, with custom options based on use case."""
    profile: Optional[str] = request.form.get('profile')
    if profile is None or profile not in MarkdownConfig.registry:
        return {
            'status': 'error',
            'error': 'not_implemented',
            'error_description': _("Unknown Markdown profile: {profile}").format(
                profile=profile
            ),
        }, 422
    text = request.form.get('text')

    html = MarkdownConfig.registry[profile].render(text)

    return {
        'status': 'ok',
        'profile': profile,
        'html': html,
    }
