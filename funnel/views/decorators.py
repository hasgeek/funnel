from functools import wraps
from flask import g, redirect, current_app, request
from funnel import app, funnelapp


def legacy_redirect(f):
    @wraps(f)
    def decorated_function(classview, **kwargs):
        if g.profile and request.method == 'GET':
            if g.profile.legacy and current_app._get_current_object() is app:
                with funnelapp.app_context(), funnelapp.test_request_context():
                    return redirect(classview.obj.url_for(classview.current_handler.name, _external=True), code=303)
            elif not g.profile.legacy and current_app._get_current_object() is funnelapp:
                with app.app_context(), app.test_request_context():
                    return redirect(classview.obj.url_for(classview.current_handler.name, _external=True), code=303)
        return f(classview, **kwargs)
    return decorated_function
