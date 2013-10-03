# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form
import wtforms
import wtforms.fields.html5

__all__=  ['ConfirmDeleteForm', 'ConfirmSessionForm']


class ConfirmDeleteForm(Form):
    """
    Confirm a delete operation
    """
    # The labels on these widgets are not used. See delete.html.
    delete = wtforms.SubmitField(__(u"Delete"))
    cancel = wtforms.SubmitField(__(u"Cancel"))


class ConfirmSessionForm(Form):
    """
    Dummy form for CSRF
    """
    pass
