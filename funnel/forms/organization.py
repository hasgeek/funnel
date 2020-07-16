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
            "Single word containing letters, numbers and dashes only. "
            "Pick something permanent: changing it will break existing links from "
            "around the web"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Profile.__name_length__),
        ],
        prefix="https://hasgeek.com/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def validate_name(self, field):
        reason = Profile.validate_name_candidate(field.data)
        if not reason:
            return  # name is available
        if reason == 'invalid':
            raise forms.ValidationError(
                _(
                    "Names can only have letters, numbers and dashes (except at the "
                    "ends)"
                )
            )
        if reason == 'reserved':
            raise forms.ValidationError(_("This name is reserved"))
        if self.edit_obj and field.data.lower() == self.edit_obj.name.lower():
            # Name is not reserved or invalid under current rules. It's also not changed
            # from existing name, or has only changed case. This is a validation pass.
            return
        if reason == 'user':
            if (
                current_auth.user.username
                and field.data.lower() == current_auth.user.username.lower()
            ):
                raise forms.ValidationError(
                    Markup(
                        _(
                            "This is <em>your</em> current username. "
                            'You must change it first from <a href="{account}">your '
                            "account</a> before you can assign it to an organization"
                        ).format(account=url_for('account'))
                    )
                )
            else:
                raise forms.ValidationError(
                    _("This name has been taken by another user")
                )
        if reason == 'org':
            raise forms.ValidationError(
                _("This name has been taken by another organization")
            )
        # We're not supposed to get an unknown reason. Flag error to developers.
        raise ValueError(f"Unknown profile name validation failure reason: {reason}")


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
