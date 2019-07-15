# -*- coding: utf-8 -*-

from functools import wraps

from flask import current_app, g, redirect, request

from .. import app, funnelapp


def legacy_redirect(f):
    """
    Redirects legacy profiles to talkfunnel and new profiles to hasgeek.
    This is based on the ``legacy`` flag of the ``Profile`` model. All
    profiles that were created before talkfunnel moved to hasgeek.com,
    have their ``legacy`` flag set.

    Ref: https://github.com/hasgeek/funnel/issues/230 (last item in checklist)
    """
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
