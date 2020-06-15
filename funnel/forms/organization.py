from flask import Markup, url_for

from baseframe import _, __
from coaster.auth import current_auth
import baseframe.forms as forms

from ..models import Organization, Profile, Team

__all__ = ['OrganizationForm', 'TeamForm']


@Organization.forms('main')
class OrganizationForm(forms.Form):
    title = forms.StringField(
        __("Organization name"),
        description=__(
            "Your organization’s given name, without legal suffixes such as Pvt Ltd"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Organization.__title_length__),
        ],
    )
    name = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "A short name for your organization’s profile page. "
            "Single word containing letters, numbers and dashes only"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Profile.__name_length__),
        ],
        prefix="https://hasgeek.com/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def validate_name(self, field):
        if self.edit_obj and field.data and field.data == self.edit_obj.name:
            # Don't validate if name is unchanged
            return

        reason = Profile.validate_name_candidate(field.data)
        if not reason:
            return  # name is available
        if reason == 'invalid':
            raise forms.ValidationError(
                _(
                    "Names can only have alphabets, numbers and dashes (except at the ends)"
                )
            )
        elif reason == 'reserved':
            raise forms.ValidationError(_("This name is reserved"))
        elif reason == 'user':
            if field.data == current_auth.user.username:
                raise forms.ValidationError(
                    Markup(
                        _(
                            "This is <em>your</em> current username. "
                            'You must change it first from <a href="{account}">your account</a> '
                            "before you can assign it to an organization"
                        ).format(account=url_for('account'))
                    )
                )
            else:
                raise forms.ValidationError(
                    _("This name has been taken by another user")
                )
        elif reason == 'org':
            raise forms.ValidationError(
                _("This name has been taken by another organization")
            )
        else:
            raise forms.ValidationError(_("This name is not available"))


@Team.forms('main')
class TeamForm(forms.Form):
    title = forms.StringField(
        __("Team name"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Team.__title_length__),
        ],
    )
    users = forms.UserSelectMultiField(
        __("Users"),
        validators=[forms.validators.DataRequired()],
        description=__("Lookup a user by their username or email address"),
    )
