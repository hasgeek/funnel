# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import QuerySelectField
from ..models import PROPOSALSTATUS

__all__ = ['TransferProposal', 'ProposalForm', 'ProposalStatusForm']


class TransferProposal(forms.Form):
    userid = forms.UserSelectField(__("Transfer to"), validators=[forms.validators.DataRequired()])


class ProposalForm(forms.Form):
    speaking = forms.RadioField(__("Are you speaking?"), coerce=int,
        choices=[(1, __(u"I will be speaking")),
                 (0, __(u"I’m proposing a topic for someone to speak on"))])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()],
        description=__("The title of your session"))
    section = QuerySelectField(__("Section"), get_label='title', validators=[forms.validators.DataRequired()],
        widget=forms.ListWidget(prefix_label=False), option_widget=forms.RadioInput())
    objective = forms.MarkdownField(__("Objective"), validators=[forms.validators.DataRequired()],
        description=__("What is the expected benefit for someone attending this?"))
    session_type = forms.RadioField(__("Session type"), validators=[forms.validators.DataRequired()], choices=[
        ('Lecture', __("Lecture")),
        ('Demo', __("Demo")),
        ('Tutorial', __("Tutorial")),
        ('Workshop', __("Workshop")),
        ('Discussion', __("Discussion")),
        ('Panel', __("Panel")),
        ])
    technical_level = forms.RadioField(__("Technical level"), validators=[forms.validators.DataRequired()], choices=[
        ('Beginner', __("Beginner")),
        ('Intermediate', __("Intermediate")),
        ('Advanced', __("Advanced")),
        ])
    description = forms.MarkdownField(__("Description"), validators=[forms.validators.DataRequired()],
        description=__("A detailed description of the session"))
    requirements = forms.MarkdownField(__("Requirements"),
        description=__("For workshops, what must participants bring to the session?"))
    slides = forms.URLField(__("Slides"), validators=[forms.validators.Optional(), forms.validators.URL()],
        description=__("Link to your slides. These can be just an outline initially. "
            "If you provide a Slideshare/Speakerdeck link, we'll embed slides in the page"))
    preview_video = forms.URLField(__("Preview Video"), validators=[forms.validators.Optional(), forms.validators.URL()],
        description=__("Link to your preview video. Use a video to engage the community and give them a better idea about what you are planning to cover in your session and why they should attend. "
            "If you provide a YouTube/Vimeo link, we'll embed it in the page"))
    links = forms.TextAreaField(__("Links"),
        description=__("Other links, one per line. Provide links to your profile and "
            "slides and videos from your previous sessions; anything that'll help "
            "folks decide if they want to attend your session"))
    bio = forms.MarkdownField(__("Speaker bio"), validators=[forms.validators.DataRequired()],
        description=__("Tell us why you are the best person to be taking this session"))
    email = forms.EmailField(__("Your email address"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        description=__("An email address we can contact you at. "
            "Not displayed anywhere"))
    phone = forms.StringField(__("Phone number"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        description=__("A phone number we can call you at to discuss your proposal, if required. "
            "Will not be displayed"))
    location = forms.StringField(__("Your location"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        description=__("Your location, to help plan for your travel if required"))


class ProposalStatusForm(forms.Form):
    status = forms.SelectField(
        __("Status"), coerce=int,
        choices=[(status, title) for (status, title) in PROPOSALSTATUS.items() if status != PROPOSALSTATUS.DRAFT])
