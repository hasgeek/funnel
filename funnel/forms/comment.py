# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms

__all__ = ['CommentForm', 'DeleteCommentForm']


class CommentForm(forms.Form):
    parent_id = forms.HiddenField(__("Parent"), default="", id="comment_parent_id")
    comment_edit_id = forms.HiddenField(__("Edit"), default="", id="comment_edit_id")
    message = forms.MarkdownField(
        __("Comment"),
        id="comment_message",
        validators=[forms.validators.DataRequired()],
    )

    def get_verbose_errors(self):
        # Temporary method to display form errors using `flash()`because
        # the comment submit view right now redirects to proposal page and
        # there is no other way to show validation errors.
        # TODO: Remove this method when comment submission is a JS request.
        verbose_error_list = []
        for field_name, errors in self.errors.items():
            field = getattr(self, field_name)
            for err in errors:
                verbose_error_list.append(
                    "{label}: {error}".format(label=field.label.text, error=err)
                )
        return verbose_error_list


class DeleteCommentForm(forms.Form):
    comment_id = forms.HiddenField(
        __("Comment"), validators=[forms.validators.DataRequired()]
    )
