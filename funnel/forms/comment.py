from __future__ import annotations

from baseframe import __, forms

from ..models import Comment, Commentset

__all__ = ['CommentForm', 'CommentsetSubscribeForm']


@Comment.forms('main')
class CommentForm(forms.Form):
    """Post or edit a comment."""

    message = forms.MarkdownField(
        "",
        id="comment_message",
        validators=[forms.validators.DataRequired()],
    )


@Commentset.forms('subscribe')
class CommentsetSubscribeForm(forms.Form):
    """Subscribe to comments."""

    subscribe = forms.BooleanField(
        '',
        description=__("Get notifications"),
        validators=[forms.validators.InputRequired()],
    )
