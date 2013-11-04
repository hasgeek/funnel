# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField
import wtforms
import wtforms.fields.html5

__all__ = ['CommentForm', 'DeleteCommentForm']


class CommentForm(Form):
    parent_id = wtforms.HiddenField(__("Parent"), default="", id="comment_parent_id")
    comment_edit_id = wtforms.HiddenField(__("Edit"), default="", id="comment_edit_id")
    message = MarkdownField(__("Add comment"), id="comment_message", validators=[wtforms.validators.Required()])


class DeleteCommentForm(Form):
    comment_id = wtforms.HiddenField(__("Comment"), validators=[wtforms.validators.Required()])


