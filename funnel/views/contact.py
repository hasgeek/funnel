# -*- coding: utf-8 -*-
from flask import jsonify, make_response, current_app, render_template, url_for, redirect
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from coaster.auth import current_auth
from coaster.views import requestargs
from coaster.utils import midnight_to_utc, utcnow
from .. import app, funnelapp, lastuser
from ..models import (db, Participant, ContactExchange)
from funnel.util import format_twitter_handle


def contact_details(participant):
    if participant:
        return {
            'fullname': participant.fullname,
            'company': participant.company,
            'email': participant.email,
            'twitter': format_twitter_handle(participant.twitter),
            'phone': participant.phone,
            }


@app.route('/account/contacts')
@lastuser.requires_login
def contacts():
    return render_template('contacts.html.jinja2')


@funnelapp.route('/account/contacts', endpoint='contacts')
def talkfunnel_contacts():
    with app.app_context(), app.test_request_context():
        return redirect(url_for('contacts', _external=True))


@app.route('/account/contacts/connect', methods=['POST'])
@lastuser.requires_login
@requestargs('puk', 'key')
def connect(puk, key):
    participant = Participant.query.filter_by(puk=puk, key=key).first()
    if not participant:
        return make_response(jsonify(status='error',
            message=u"Attendee details not found"), 404)
    project = participant.project
    if project.date_upto:
        if midnight_to_utc(project.date_upto + timedelta(days=1), project.timezone) < utcnow():
            return make_response(jsonify(status='error',
                message=u"This project has concluded"), 401)

        try:
            contact_exchange = ContactExchange(user=current_auth.actor,
                participant=participant)
            db.session.add(contact_exchange)
            db.session.commit()
        except IntegrityError:
            current_app.logger.warning(u"Contact Exchange already present")
            db.session.rollback()
        return jsonify(contact=contact_details(participant))
    else:
        return make_response(jsonify(status='error',
            message=u"Unauthorized contact exchange"), 403)
