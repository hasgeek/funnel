from flask import render_template
from flask_mailman import Message

from html2text import html2text

from baseframe import _

from .. import mail


def send_email_verify_link(useremail):
    """
    Mail a verification link to the user.
    """
    msg = Message(subject=_("Confirm your email address"), recipients=[useremail.email])
    msg.html = render_template('account_emailverify.html.jinja2', useremail=useremail)
    msg.body = html2text(msg.html)
    mail.send(msg)


def send_password_reset_link(email, user, secret):
    msg = Message(subject=_("Reset your password"), recipients=[email])
    msg.html = render_template(
        'account_emailreset.html.jinja2', user=user, secret=secret
    )
    msg.body = html2text(msg.html)
    mail.send(msg)
