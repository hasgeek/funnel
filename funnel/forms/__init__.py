# -*- coding: utf-8 -*-

from baseframe.forms import Form, MarkdownField
import wtforms
import wtforms.fields.html5
from wtforms.ext.sqlalchemy.fields import QuerySelectField


class ProposalSpaceForm(Form):
    name = wtforms.TextField('URL name', validators=[wtforms.validators.Required()])
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()])
    datelocation = wtforms.TextField('Date and Location', validators=[wtforms.validators.Required()])
    date = wtforms.DateField('Date (for sorting)',
            validators=[wtforms.validators.Required('Enter a valid date in YYYY-MM-DD format.')])
    tagline = wtforms.TextField('Tagline', validators=[wtforms.validators.Required()])
    description = wtforms.TextAreaField('Description', validators=[wtforms.validators.Required()])
    status = wtforms.SelectField('Status', coerce=int, choices=[
        (0, 'Draft'),
        (1, 'Open'),
        (2, 'Voting'),
        (3, 'Jury selection'),
        (4, 'Feedback'),
        (5, 'Closed'),
        (6, 'Rejected'),
        ])


class SectionForm(Form):
    name = wtforms.TextField('URL name', validators=[wtforms.validators.Required()])
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()])
    description = wtforms.TextAreaField('Description', validators=[wtforms.validators.Required()])
    public = wtforms.BooleanField('Public?')


class UserGroupForm(Form):
    name = wtforms.TextField('URL name', validators=[wtforms.validators.Required()])
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()])
    users = wtforms.TextAreaField('Users', validators=[wtforms.validators.Required()],
        description="Usernames or email addresses, one per line")


class ProposalForm(Form):
    email = wtforms.fields.html5.EmailField('Your email address', validators=[wtforms.validators.Required()],
        description="An email address we can contact you at. "
            "Not displayed anywhere")
    phone = wtforms.TextField('Phone number', validators=[wtforms.validators.Required()],
        description="A phone number we can call you at to discuss your proposal, if required. "
            "Will not be displayed")
    speaking = wtforms.RadioField("Are you speaking?", coerce=int,
        choices=[(1, u"I will be speaking"),
                 (0, u"I’m proposing a topic for someone to speak on")])
    title = wtforms.TextField('Title', validators=[wtforms.validators.Required()],
        description="The title of your session")
    section = QuerySelectField('Section', get_label='title', validators=[wtforms.validators.Required()],
        widget=wtforms.widgets.ListWidget(prefix_label=False), option_widget=wtforms.widgets.RadioInput())
    objective = MarkdownField('Objective', validators=[wtforms.validators.Required()],
        description="What is the expected benefit for someone attending this?")
    session_type = wtforms.RadioField('Session type', validators=[wtforms.validators.Required()], choices=[
        ('Lecture', 'Lecture'),
        ('Demo', 'Demo'),
        ('Tutorial', 'Tutorial'),
        ('Workshop', 'Workshop'),
        ('Discussion', 'Discussion'),
        ('Panel', 'Panel'),
        ])
    technical_level = wtforms.RadioField('Technical level', validators=[wtforms.validators.Required()], choices=[
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ])
    description = MarkdownField('Description', validators=[wtforms.validators.Required()],
        description="A detailed description of the session")
    requirements = MarkdownField('Requirements',
        description="For workshops, what must participants bring to the session?")
    slides = wtforms.fields.html5.URLField('Slides', validators=[wtforms.validators.Optional(), wtforms.validators.URL()],
        description="Link to your slides. These can be just an outline initially. "
            "If you provide a Slideshare link, we'll embed slides in the page")
    links = wtforms.TextAreaField('Links',
        description="Other links, one per line. Provide links to your profile and "
            "slides and videos from your previous sessions; anything that'll help "
            "folks decide if they want to attend your session")
    bio = MarkdownField('Speaker bio', validators=[wtforms.validators.Required()],
        description="Tell us why you are the best person to be taking this session")


class CommentForm(Form):
    parent_id = wtforms.HiddenField('Parent', default="", id="comment_parent_id")
    comment_edit_id = wtforms.HiddenField('Edit', default="", id="comment_edit_id")
    message = wtforms.TextAreaField('Add comment', id="comment_message", validators=[wtforms.validators.Required()])


class DeleteCommentForm(Form):
    comment_id = wtforms.HiddenField('Comment', validators=[wtforms.validators.Required()])


class ConfirmDeleteForm(Form):
    """
    Confirm a delete operation
    """
    # The labels on these widgets are not used. See delete.html.
    delete = wtforms.SubmitField(u"Delete")
    cancel = wtforms.SubmitField(u"Cancel")


class ConfirmSessionForm(Form):
    """
    Dummy form for CSRF
    """
    pass
