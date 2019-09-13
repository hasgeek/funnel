# -*- coding: utf-8 -*-

from baseframe import _, __
from baseframe.forms.sqlalchemy import QuerySelectField
import baseframe.forms as forms


class NewProfileForm(forms.Form):
    """Create a new profile."""

    profile = forms.RadioField(
        __("Organization"),
        validators=[forms.validators.DataRequired("Select an organization")],
        description=__(
            u"Select the organization you’d like to create a Talkfunnel for"
        ),
    )


class EditProfileForm(forms.Form):
    """Edit a profile."""

    description = forms.MarkdownField(
        __("Welcome message"),
        validators=[
            forms.validators.DataRequired(
                _(u"Please write a message for the landing page")
            )
        ],
        description=__("This welcome message will be shown on the landing page."),
    )
    logo_url = forms.URLField(
        __("Logo URL"),
        description=__("Profile logo"),
        validators=[
            forms.validators.Optional(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
    )
    admin_team = QuerySelectField(
        u"Admin Team",
        validators=[forms.validators.DataRequired(_(u"Please select a team"))],
        get_label='title',
        allow_blank=True,
        blank_text=__("Choose a team..."),
        description=__(
            "The team of users with administrative rights to this Profile (owners always have admin access)"
        ),
    )

    def set_queries(self):
        self.admin_team.query = self.edit_obj.teams
