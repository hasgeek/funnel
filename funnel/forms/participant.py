from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

from baseframe import __
import baseframe.forms as forms

from ..models import Participant

__all__ = ['ParticipantBadgeForm', 'ParticipantForm']


@Participant.forms('main')
class ParticipantForm(forms.Form):
    fullname = forms.StringField(
        __("Fullname"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    email = forms.EmailField(
        __("Email"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    phone = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    city = forms.StringField(
        __("City"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    company = forms.StringField(
        __("Company"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    job_title = forms.StringField(
        __("Job title"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    twitter = forms.StringField(
        __("Twitter"),
        validators=[forms.validators.Length(max=15)],
        filters=[forms.filters.strip()],
    )
    badge_printed = forms.BooleanField(__("Badge is printed"))
    events = QuerySelectMultipleField(
        __("Events"),
        widget=ListWidget(),
        option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired("Select at least one event")],
    )

    def set_queries(self):
        if self.edit_parent is not None:
            self.events.query = self.edit_parent.events


@Participant.forms('badge')
class ParticipantBadgeForm(forms.Form):
    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField(
        "", choices=[(val_title[0], val_title[1]) for val_title in choices]
    )
