from functools import wraps
from flask import g, request, redirect, current_app
from funnel import app, funnelapp


def legacy_redirect(f):
    @wraps(f)
    def decorated_function(clview, **kwargs):
        if g.profile:
            if g.profile.legacy and current_app == app:
                with funnelapp.app_context(), funnelapp.test_request_context():
                    return redirect(clview.obj.url_for(_external=True), code=303)
            elif not g.profile.legacy and current_app == funnelapp:
                with app.app_context(), app.test_request_context():
                    return redirect(clview.obj.url_for(_external=True), code=303)
        return f(clview, **kwargs)
    return decorated_function
