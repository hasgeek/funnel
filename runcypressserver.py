#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from flask import redirect, request, session

from funnel import app
from funnel.models import User


@app.route('/testlogin')
def testlogin():
    nexturl = request.args.get('next', request.referrer)
    email = request.args.get('email')
    u = User.query.filter_by(email=email).first()
    if u is not None:
        session['lastuser_userid'] = u.userid
    return redirect(nexturl, 303)


try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 3002
app.run('0.0.0.0', port=port, debug=True)
