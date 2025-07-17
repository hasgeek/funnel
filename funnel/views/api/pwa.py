"""Progressive Web App API support endpoints."""

from flask import render_template, url_for

from baseframe import _

from ... import app
from ...typing import ReturnView


@app.route('/api/1/template/offline')
def offline() -> ReturnView:
    """Return page to be cached for when the client is offline."""
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js')
def sw() -> ReturnView:
    """Return Service Worker JavaScript."""
    return app.send_static_file('build/js/service-worker.js')


@app.route('/manifest.json')
@app.route('/manifest.webmanifest')
def manifest() -> ReturnView:
    """Return web manifest."""
    return {
        'name': app.config['SITE_TITLE'],
        'short_name': app.config['SITE_TITLE'],
        'description': _('Discussion spaces for geeks'),
        'scope': '/',
        'theme_color': '#e3e1e1',
        'background_color': '#ffffff',
        'orientation': 'portrait',
        'start_url': '/?utm_source=WebApp',
        'display': 'standalone',
        'display_override': ['tabbed'],
        'tab_strip': {
            'home_tab': {
                'scope_patterns': [
                    {'pathname': '/'},
                    {'pathname': '/?utm_source=WebApp'},
                ],
            },
        },
        'icons': [
            {
                'src': url_for('static', filename='img/hasgeek-icon-any-180x180.png'),
                'sizes': '180x180',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': url_for(
                    'static', filename='img/hasgeek-icon-maskable-192x192.png'
                ),
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'maskable',
            },
            {
                'src': url_for(
                    'static', filename='img/hasgeek-icon-maskable-512x512.png'
                ),
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'maskable',
            },
        ],
    }
