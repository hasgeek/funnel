# -*- coding: utf-8 -*-

from flask import Markup, current_app, url_for

from baseframe import _, __
from coaster.auth import current_auth
from lastuser_core.models import AccountName, Organization, Team, User
import baseframe.forms as forms

__all__ = ['OrganizationForm', 'TeamForm']


class OrganizationForm(forms.Form):
    title = forms.StringField(
        __("Organization name"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Organization.__title_length__),
        ],
    )
    name = forms.AnnotatedTextField(
        __("Username"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=AccountName.__name_length__),
        ],
        prefix="https://hasgeek.com/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def validate_name(self, field):
        if field.data.lower() in current_app.config['RESERVED_USERNAMES']:
            # To be deprecated in favour of one below
            raise forms.ValidationError(_("This name is reserved"))

        if self.edit_obj:
            reason = self.edit_obj.validate_name_candidate(field.data)
        else:
            reason = AccountName.validate_name_candidate(field.data)
        if not reason:
            return  # AccountName is available
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
        lastuser=None,
        usermodel=User,
        autocomplete_endpoint=lambda: url_for('lastuser_oauth.user_autocomplete'),
        getuser_endpoint=lambda: url_for('lastuser_oauth.user_get_by_userids'),
    )
