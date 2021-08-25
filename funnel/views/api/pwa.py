from flask import render_template

from ... import app


@app.route('/api/1/template/offline')
def offline():
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('build/js/service-worker.js')
