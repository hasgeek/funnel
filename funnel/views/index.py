# -*- coding: utf-8 -*-

from flask import render_template
from .. import app, lastuser
from ..models import ProposalSpace
from coaster.views import jsonp
from .space import space_data


@app.route('/')
def index():
    spaces = ProposalSpace.query.filter(ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
    return render_template('index.html', spaces=spaces, siteadmin=lastuser.has_permission('siteadmin'))

@app.route('/json')
def spaces_json():
	return jsonp(spaces=[space_data(space) for space in ProposalSpace.query.all()])