# -*- coding: utf-8 -*-

import flask.ext.wtf as wtf

from models import SPACESTATUS, ProposalSpaceSection


class ProposalSpaceForm(wtf.Form):
    name = wtf.TextField('URL name', validators=[wtf.Required()])
    title = wtf.TextField('Title', validators=[wtf.Required()])
    datelocation = wtf.TextField('Date and Location', validators=[wtf.Required()])
    date = wtf.DateField('Date (for sorting)', validators=[wtf.Required()])
    tagline = wtf.TextField('Tagline', validators=[wtf.Required()])
    description = wtf.TextAreaField('Description', validators=[wtf.Required()])
    status = wtf.SelectField('Status', coerce=int, choices=[
        (0, 'Draft'),
        (1, 'Open'),
        (2, 'Voting'),
        (3, 'Jury selection'),
        (4, 'Feedback'),
        (5, 'Closed'),
        (6, 'Rejected'),
        ])


class SectionForm(wtf.Form):
    name = wtf.TextField('URL name', validators=[wtf.Required()])
    title = wtf.TextField('Title', validators=[wtf.Required()])
    description = wtf.TextAreaField('Description', validators=[wtf.Required()])
    public = wtf.BooleanField('Public?')


class ProposalForm(wtf.Form):
    email = wtf.html5.EmailField('Your email address', validators=[wtf.Required()],
        description="An email address we can contact you at. "\
            "Not displayed anywhere")
    phone = wtf.TextField('Phone number', validators=[wtf.Required()],
        description="A phone number we can call you at to discuss your proposal, if required. "
            "Will not be displayed")
    speaking = wtf.RadioField("Are you speaking?", coerce=int,
        choices=[(1, u"I will be speaking"),
                 (0, u"I’m proposing a topic for someone to speak on")])
    title = wtf.TextField('Title', validators=[wtf.Required()],
        description="The title of your session")
    section = wtf.QuerySelectField('Section', get_label='title', validators=[wtf.Required()],
        widget=wtf.ListWidget(prefix_label=False), option_widget=wtf.RadioInput())
    objective = wtf.TextAreaField('Objective', validators=[wtf.Required()],
        description="What is the expected benefit for someone attending this?")
    session_type = wtf.RadioField('Session type', validators=[wtf.Required()], choices=[
        ('Lecture', 'Lecture'),
        ('Demo', 'Demo'),
        ('Tutorial', 'Tutorial'),
        ('Workshop', 'Workshop'),
        ('Discussion', 'Discussion'),
        ('Panel', 'Panel'),
        ])
    technical_level = wtf.RadioField('Technical level', validators=[wtf.Required()], choices=[
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ])
    description = wtf.TextAreaField('Description', validators=[wtf.Required()],
        description="A detailed description of the session")
    requirements = wtf.TextAreaField('Requirements',
        description="For workshops, what must participants bring to the session?")
    slides = wtf.html5.URLField('Slides', validators=[wtf.Optional(), wtf.URL()],
        description="Link to your slides. These can be just an outline initially. "\
            "If you provide a Slideshare link, we'll embed slides in the page")
    links = wtf.TextAreaField('Links',
        description="Other links, one per line. Provide links to your profile and "\
            "slides and videos from your previous sessions; anything that'll help "\
            "folks decide if they want to attend your session")
    bio = wtf.TextAreaField('Speaker bio', validators=[wtf.Required()],
        description="Tell us why you are the best person to be taking this session")


class CommentForm(wtf.Form):
    parent_id = wtf.HiddenField('Parent', default="", id="comment_parent_id")
    edit_id = wtf.HiddenField('Edit', default="", id="comment_edit_id")
    message = wtf.TextAreaField('Add comment', id="comment_message", validators=[wtf.Required()])


class DeleteCommentForm(wtf.Form):
    comment_id = wtf.HiddenField('Comment', validators=[wtf.Required()])


class ConfirmDeleteForm(wtf.Form):
    """
    Confirm a delete operation
    """
    # The labels on these widgets are not used. See delete.html.
    delete = wtf.SubmitField(u"Delete")
    cancel = wtf.SubmitField(u"Cancel")
