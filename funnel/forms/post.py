from baseframe import __
import baseframe.forms as forms

from ..models import Post

__all__ = ['PostForm']


@Post.forms('main')
class PostForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    body = forms.MarkdownField(
        __("Post body"),
        validators=[forms.validators.DataRequired()],
        description=__("Post content"),
    )
    is_pinned = forms.BooleanField(
        __("Make this update pinned"),
        default=False,
        description=__("If checked, update will be pinned to the top"),
    )
    restricted = forms.BooleanField(
        __("Make this update visible only to participants"),
        default=False,
        description=__("If checked, update will be visible only to participants"),
    )
