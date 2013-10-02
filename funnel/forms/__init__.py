# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5
from wtforms.ext.sqlalchemy.fields import QuerySelectField


class ProposalSpaceForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName()])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    datelocation = wtforms.TextField(__("Date and Location"), validators=[wtforms.validators.Required()])
    date = wtforms.DateField(__("Date (for sorting)"),
        validators=[wtforms.validators.Required(__("Enter a valid date in YYYY-MM-DD format"))],
        description=__("In YYYY-MM-DD format"))
    tagline = wtforms.TextField(__("Tagline"), validators=[wtforms.validators.Required()],
        description=__("This is displayed on the card on the homepage"))
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()],
        description=__("Instructions for proposers, with Markdown formatting"))
    status = wtforms.SelectField(__("Status"), coerce=int, choices=[
        (0, __("Draft")),
        (1, __("Open")),
        (2, __("Voting")),
        (3, __("Jury selection")),
        (4, __("Feedback")),
        (5, __("Closed")),
        (6, __("Withdrawn")),
        ],
        description=__(u"Proposals can only be submitted in the “Open” state. "
            u"“Closed” and “Withdrawn” are hidden from homepage"))


class SectionForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName(scoped=True)])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    description = wtforms.TextAreaField(__("Description"), validators=[wtforms.validators.Required()])
    public = wtforms.BooleanField(__("Public?"), default=True)


class UserGroupForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName(scoped=True)])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    users = wtforms.TextAreaField(__("Users"), validators=[wtforms.validators.Required()],
        description=__("Usernames or email addresses, one per line"))


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


class CommentForm(Form):
    parent_id = wtforms.HiddenField(__("Parent"), default="", id="comment_parent_id")
    comment_edit_id = wtforms.HiddenField(__("Edit"), default="", id="comment_edit_id")
    message = MarkdownField(__("Add comment"), id="comment_message", validators=[wtforms.validators.Required()])


class DeleteCommentForm(Form):
    comment_id = wtforms.HiddenField(__("Comment"), validators=[wtforms.validators.Required()])


class ConfirmDeleteForm(Form):
    """
    Confirm a delete operation
    """
    # The labels on these widgets are not used. See delete.html.
    delete = wtforms.SubmitField(__(u"Delete"))
    cancel = wtforms.SubmitField(__(u"Cancel"))


class ConfirmSessionForm(Form):
    """
    Dummy form for CSRF
    """
    pass
