"""Progressive Web App API support endpoints."""

from flask import render_template

from ... import app


@app.route('/api/1/template/offline')
def offline():
    """Return page to be cached for when the client is offline."""
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js')
def sw():
    """Return Service Worker JavaScript."""
    return app.send_static_file('build/js/service-worker.js')
