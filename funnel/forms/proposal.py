# -*- coding: utf-8 -*-

from wtforms.fields import FieldList, FormField
from wtforms.widgets import ListWidget, CheckboxInput
from baseframe import __
import baseframe.forms as forms
from flask import g
from baseframe.forms.sqlalchemy import QuerySelectField, QuerySelectMultipleField
from ..models import Project, Profile, Label
from .label import SublabelForm

__all__ = ['TransferProposal', 'ProposalForm', 'ProposalTransitionForm', 'ProposalLabelsForm',
    'ProposalMoveForm', 'get_proposal_labels_form']


def get_proposal_labels_form(base_form_class, *args, **kwargs):
    """
    Takes a proposal form class as base form and adds the labelset fields to it.
    Dynamic fields can only be added to the form class and not instance. Hence this.
    Any form that has `obj=<proposal_object>` or `parent=<proposal_parent_obj>`
    passed to it, can be used with this function.
    `parent` kwarg must be provided, otherwise the labels wont be added to the form.
    """
    if 'parent' in kwargs or 'obj' in kwargs:
        # we need parent project to be able to handle labelsets
        project = kwargs.get('parent', None) or kwargs.get('obj').project
        for label in project.labels:
            ls_name = label.name
            if not hasattr(base_form_class, ls_name):
                if label.restricted and not set(project.current_roles).intersection({'admin', 'reviewer'}):
                    continue
                if label.is_parent:
                    FieldType = forms.RadioField
                    validators = [forms.validators.DataRequired()] if label.required else []
                    setattr(base_form_class, ls_name, FieldType(label.title, validators=validators,
                        choices=[(subl.name, subl.title) for subl in label.children], description=label.description))
                else:
                    FieldType = forms.BooleanField
                    validators = [forms.validators.DataRequired()] if label.required else []
                    setattr(base_form_class, ls_name, FieldType(label.title, validators=validators))
    return base_form_class(*args, **kwargs)


class TransferProposal(forms.Form):
    userid = forms.UserSelectField(__("Transfer to"), validators=[forms.validators.DataRequired()])


class ProposalLabelsForm(forms.Form):
    labelsets = FormField(forms.Form)

    def set_queries(self):
        self.labelsets.form = get_proposal_labels_form(forms.Form, obj=self.edit_obj, parent=self.edit_parent)


class ProposalForm(forms.Form):
    speaking = forms.RadioField(__("Are you speaking?"), coerce=int,
        choices=[(1, __(u"I will be speaking")),
                 (0, __(u"I’m proposing a topic for someone to speak on"))])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()],
        description=__("The title of your session"))
    objective = forms.MarkdownField(__("Objective"), validators=[forms.validators.DataRequired()],
        description=__("What is the expected benefit for someone attending this?"))
    description = forms.MarkdownField(__("Description"), validators=[forms.validators.DataRequired()],
        description=__("A detailed description of the session"))
    requirements = forms.MarkdownField(__("Requirements"),
        description=__("For workshops, what must participants bring to the session?"))
    slides = forms.URLField(__("Slides"),
        validators=[forms.validators.Optional(), forms.validators.URL(), forms.validators.Length(max=2000)],
        description=__("Link to your slides. These can be just an outline initially. "
            "If you provide a Slideshare/Speakerdeck link, we'll embed slides in the page"))
    preview_video = forms.URLField(__("Preview Video"),
        validators=[forms.validators.Optional(), forms.validators.URL(), forms.validators.Length(max=2000)],
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

    labelsets = FormField(forms.Form)

    def __init__(self, *args, **kwargs):
        super(ProposalForm, self).__init__(*args, **kwargs)
        project = kwargs.get('parent')
        if project.proposal_part_a.get('title'):
            self.objective.label.text = project.proposal_part_a.get('title')
        if project.proposal_part_a.get('hint'):
            self.objective.description = project.proposal_part_a.get('hint')
        if project.proposal_part_b.get('title'):
            self.description.label.text = project.proposal_part_b.get('title')
        if project.proposal_part_b.get('hint'):
            self.description.description = project.proposal_part_b.get('hint')

    def set_queries(self):
        self.labelsets.form = get_proposal_labels_form(forms.Form, obj=self.edit_obj, parent=self.edit_parent)


class ProposalTransitionForm(forms.Form):
    transition = forms.SelectField(__("Status"), validators=[forms.validators.DataRequired()])

    def set_queries(self):
        """
        value: transition method name
        label: transition object itself
        We need the whole object to get the additional metadata in templates
        """
        self.transition.choices = self.edit_obj.state.transitions().items()


class ProposalMoveForm(forms.Form):
    target = QuerySelectField(__("Move proposal to"), validators=[
                              forms.validators.DataRequired()], get_label='title')

    def set_queries(self):
        team_ids = [t.id for t in g.user.teams]
        self.target.query = Project.query.join(Project.profile).filter(
            (Project.admin_team_id.in_(team_ids)) |
            (Profile.admin_team_id.in_(team_ids))
            ).order_by(Project.date.desc())
