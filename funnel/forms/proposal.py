# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from flask import g
from baseframe.forms.sqlalchemy import QuerySelectField
from ..models import Project, Profile, Proposal, Label, Labelset

__all__ = ['TransferProposal', 'ProposalForm', 'ProposalTransitionForm', 'ProposalMoveForm']


class TransferProposal(forms.Form):
    userid = forms.UserSelectField(__("Transfer to"), validators=[forms.validators.DataRequired()])


class _ProposalFormInner(forms.Form):
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

    def __init__(self, *args, **kwargs):
        super(_ProposalFormInner, self).__init__(*args, **kwargs)
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
        for labelset in self.edit_parent.labelsets:
            labels_data = set(self.edit_obj.labels).intersection(set(labelset.labels))
            data = labels_data.pop().name if len(labels_data) == 1 else [l.name for l in labels_data]
            labelset_field = getattr(self, labelset.form_name)
            if labelset_field.data == 'None' and data:
                labelset_field.data = data

    def populate_obj_labels(self, proposal):
        """
        Assign the appropriate labels to the proposal
        """
        for key in self.data.keys():
            if key.startswith('labelset_'):
                labelset = Labelset.query.filter_by(form_name=key, project=proposal.project).first()
                # in case of MultiSelectField, self.data.get(key) is a list
                label_names = self.data.get(key) if isinstance(self.data.get(key), list) else [self.data.get(key)]
                if labelset.radio_mode:
                    for lname in label_names:
                        label = Label.query.filter_by(labelset=labelset, name=lname).first()
                        proposal.assign_label(label)
                else:
                    existing_labels = set(labelset.labels).intersection(set(proposal.labels))
                    for elabel in existing_labels:
                        proposal.labels.remove(elabel)
                    for lname in label_names:
                        label = Label.query.filter_by(labelset=labelset, name=lname).first()
                        proposal.assign_label(label)


class ProposalForm(object):
    def __new__(self, *args, **kwargs):
        """
        Proxy object that intercepts ProposalForm initiation and adds the
        dynamic fields for the labelsets to the form. The dynamic fields
        need to be added to the Form class, hence this. This way the regular
        way of using ProposalForm doesn't change.
        """
        proposal_form = _ProposalFormInner

        if 'parent' in kwargs:
            # we need parent project to be able to handle labelsets
            project = kwargs.get('parent')
            for labelset in project.labelsets:
                ls_name = labelset.form_name
                if not hasattr(self, ls_name):
                    if labelset.restricted and not set(project.current_roles).intersection({'admin', 'reviewer'}):
                        continue
                    FieldType = forms.RadioField if labelset.radio_mode else forms.SelectMultipleField
                    validators = [forms.validators.DataRequired()] if labelset.required else []
                    if 'obj' in kwargs:
                        # Edit form
                        choices = [(l.name, l.title) for l in labelset.labels]
                    setattr(proposal_form, ls_name, FieldType(labelset.title, validators=validators,
                        choices=choices, description=labelset.description))

        return _ProposalFormInner(*args, **kwargs)


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
