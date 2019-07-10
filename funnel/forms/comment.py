# -*- coding: utf-8 -*-

import baseframe.forms as forms
from baseframe import __

__all__ = ['CommentForm', 'DeleteCommentForm']


class CommentForm(forms.Form):
    parent_id = forms.HiddenField(__("Parent"), default="", id="comment_parent_id")
    comment_edit_id = forms.HiddenField(__("Edit"), default="", id="comment_edit_id")
    message = forms.MarkdownField(__("Comment"), id="comment_message", validators=[forms.validators.DataRequired()])


class DeleteCommentForm(forms.Form):
    comment_id = forms.HiddenField(__("Comment"), validators=[forms.validators.DataRequired()])
