# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField
import wtforms
import wtforms.fields.html5
from wtforms.ext.sqlalchemy.fields import QuerySelectField

__all__ = ['ProposalForm']


class ProposalForm(Form):
    email = wtforms.fields.html5.EmailField(__("Your email address"), validators=[wtforms.validators.Required()],
        description=__("An email address we can contact you at. "
            "Not displayed anywhere"))
    phone = wtforms.TextField(__("Phone number"), validators=[wtforms.validators.Required()],
        description=__("A phone number we can call you at to discuss your proposal, if required. "
            "Will not be displayed"))
    speaking = wtforms.RadioField(__("Are you speaking?"), coerce=int,
        choices=[(1, __(u"I will be speaking")),
                 (0, __(u"I’m proposing a topic for someone to speak on"))])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()],
        description=__("The title of your session"))
    section = QuerySelectField(__("Section"), get_label='title', validators=[wtforms.validators.Required()],
        widget=wtforms.widgets.ListWidget(prefix_label=False), option_widget=wtforms.widgets.RadioInput())
    objective = MarkdownField(__("Objective"), validators=[wtforms.validators.Required()],
        description=__("What is the expected benefit for someone attending this?"))
    session_type = wtforms.RadioField(__("Session type"), validators=[wtforms.validators.Required()], choices=[
        ('Lecture', __("Lecture")),
        ('Demo', __("Demo")),
        ('Tutorial', __("Tutorial")),
        ('Workshop', __("Workshop")),
        ('Discussion', __("Discussion")),
        ('Panel', __("Panel")),
        ])
    technical_level = wtforms.RadioField(__("Technical level"), validators=[wtforms.validators.Required()], choices=[
        ('Beginner', __("Beginner")),
        ('Intermediate', __("Intermediate")),
        ('Advanced', __("Advanced")),
        ])
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()],
        description=__("A detailed description of the session"))
    requirements = MarkdownField(__("Requirements"),
        description=__("For workshops, what must participants bring to the session?"))
    slides = wtforms.fields.html5.URLField(__("Slides"), validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description=__("Link to your slides. These can be just an outline initially. "
            "If you provide a Slideshare link, we'll embed slides in the page"))
    links = wtforms.TextAreaField(__("Links"),
        description=__("Other links, one per line. Provide links to your profile and "
            "slides and videos from your previous sessions; anything that'll help "
            "folks decide if they want to attend your session"))
    bio = MarkdownField(__("Speaker bio"), validators=[wtforms.validators.Required()],
        description=__("Tell us why you are the best person to be taking this session"))
