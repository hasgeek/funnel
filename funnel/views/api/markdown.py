"""Markdown preview view."""


from flask import request

from ... import app
from ...typing import ReturnView
from ...utils.markdown import markdown

extra_markdown_types = {'profile', 'project', 'submission', 'session'}


@app.route('/api/1/preview/markdown', methods=['POST'])
def markdown_preview() -> ReturnView:
    """Render Markdown in the backend, with custom options based on use case."""
    mtype = request.form.get('type')
    text = request.form.get('text')

    html = markdown(text)

    return {
        'status': 'ok',
        'type': mtype if mtype in extra_markdown_types else None,
        'html': html,
    }
