# -*- coding: utf-8 -*-

from flask import render_template
from .. import app, lastuser
from ..models import ProposalSpace


@app.route('/')
def index():
    spaces = ProposalSpace.query.filter(ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
    return render_template('index.html', spaces=spaces, siteadmin=lastuser.has_permission('siteadmin'))
