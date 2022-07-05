"""Progressive Web App API support endpoints."""

from flask import jsonify, render_template, url_for

from baseframe import _

from ... import app


@app.route('/api/1/template/offline')
def offline():
    """Return page to be cached for when the client is offline."""
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js')
def sw():
    """Return Service Worker JavaScript."""
    return app.send_static_file('build/js/service-worker.js')


@app.route('/manifest.json')
@app.route('/manifest.webmanifest')
def manifest():
    """Return web manifest."""
    return jsonify(
        {
            'name': app.config['SITE_TITLE'],
            'short_name': app.config['SITE_TITLE'],
            'description': _('Discussion spaces for geeks'),
            'scope': '/',
            'theme_color': '#e3e1e1',
            'background_color': '#ffffff',
            'display': 'standalone',
            'orientation': 'portrait',
            'start_url': '/?utm_source=WebApp',
            'icons': [
                {
                    'src': url_for(
                        'static', filename='img/android-chrome-192x192.png', v=2
                    ),
                    'sizes': '192x192',
                    'type': 'image/png',
                    'purpose': 'any',
                },
                {
                    'src': url_for(
                        'static', filename='img/android-chrome-512x512.png', v=2
                    ),
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any',
                },
            ],
        }
    )
