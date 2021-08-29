from flask import request

from coaster.utils import markdown
from coaster.views import render_with

from ... import app
from ...models import markdown_content_options

extra_markdown_types = {'profile', 'project', 'submission', 'session'}


@app.route('/api/1/preview/markdown', methods=['POST'])
@render_with(json=True)
def markdown_preview():
    mtype = request.form.get('type')
    text = request.form.get('text')
    if mtype in extra_markdown_types:
        markdown_options = markdown_content_options
    else:
        markdown_options = {}

    html = markdown(text, **markdown_options)

    return {
        'status': 'ok',
        'type': mtype if mtype in extra_markdown_types else None,
        'html': html,
    }
