# -*- coding: utf-8 -*-

from flask import render_template
from coaster.views import load_model
from baseframe import _
from .. import app, lastuser
from ..models import ProposalSpace


@app.route('/<space>/schedule')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_view(space):
    return render_template('schedule.html', space=space, venues=space.venues,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('schedule'), _("Schedule"))])
