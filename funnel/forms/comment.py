from __future__ import annotations

import baseframe.forms as forms

from ..models import Comment

__all__ = ['CommentForm']


@Comment.forms('main')
class CommentForm(forms.Form):
    message = forms.MarkdownField(
        "",
        id="comment_message",
        validators=[forms.validators.DataRequired()],
    )
