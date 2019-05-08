# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from flask import g
from baseframe.forms.sqlalchemy import QuerySelectField
from ..models import Project, Profile

__all__ = ['TransferProposal', 'ProposalForm', 'ProposalTransitionForm', 'ProposalLabelsForm',
    'ProposalMoveForm', 'ProposalLabelsAdminForm']


class ClearableRadioField(forms.RadioField):
    def validate(self, form, extra_validators=()):
        if getattr(form.edit_obj, self.name) is None and not self.raw_data:
            # The object has no value for this label and request sent no value for it
            return True
        else:
            return super(ClearableRadioField, self).validate(form, extra_validators)

    def populate_obj(self, obj, name):
        if self.data in dict(self.choices):
            setattr(obj, name, self.data)


def proposal_label_form(project, proposal):
    """
    Returns a label form for the given project and proposal.
    """
    class ProposalLabelForm(forms.Form):
        pass

    for label in project.labels:
        if label.has_options and not label.archived and not label.restricted:
            setattr(ProposalLabelForm, label.name, forms.RadioField(
                label.form_label_text,
                description=label.description,
                validators=[forms.validators.DataRequired(__("Please select one"))] if label.required else [],
                choices=[(option.name, option.title) for option in label.options if not option.archived]
            ))

    return ProposalLabelForm(obj=proposal.formlabels if proposal else None, meta={'csrf': False})


def proposal_label_admin_form(project, proposal):
    """
    Returns a label form to use in admin panel for given project and proposal
    """
    class ProposalLabelAdminForm(forms.Form):
        pass

    for label in project.labels:
        if label.is_for_admin:
            form_kwargs = {}
            if label.has_options:
                FieldType = ClearableRadioField
                form_kwargs['choices'] = [(option.name, option.title) for option in label.options if not option.archived]
            else:
                FieldType = forms.BooleanField

            setattr(ProposalLabelAdminForm, label.name, FieldType(
                label.form_label_text,
                description=label.description,
                validators=[],  # required validator is only needed on proposal edit form, not the admin form
                **form_kwargs
            ))

    return ProposalLabelAdminForm(obj=proposal.formlabels if proposal else None, meta={'csrf': False})


class TransferProposal(forms.Form):
    userid = forms.UserSelectField(__("Transfer to"), validators=[forms.validators.DataRequired()])


class ProposalLabelsForm(forms.Form):
    formlabels = forms.FormField(forms.Form, __("Labels"))

    def set_queries(self):
        self.formlabels.form = proposal_label_form(project=self.edit_parent, proposal=self.edit_obj)


class ProposalLabelsAdminForm(forms.Form):
    formlabels = forms.FormField(forms.Form, __("Labels"))

    def set_queries(self):
        self.formlabels.form = proposal_label_admin_form(project=self.edit_parent, proposal=self.edit_obj)


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

    formlabels = forms.FormField(forms.Form, __("Labels"))

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
        self.formlabels.form = proposal_label_form(project=self.edit_parent, proposal=self.edit_obj)


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
    target = QuerySelectField(__("Move proposal to"),
        validators=[forms.validators.DataRequired()], get_label='title')

    def set_queries(self):
        team_ids = [t.id for t in g.user.teams]
        self.target.query = Project.query.join(Project.profile).filter(
            (Project.admin_team_id.in_(team_ids)) | (Profile.admin_team_id.in_(team_ids))
        ).order_by(Project.date.desc())
