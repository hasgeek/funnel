from __future__ import annotations

from typing import Optional

from baseframe import __
from baseframe.forms.sqlalchemy import QuerySelectField
from coaster.auth import current_auth
import baseframe.forms as forms

from ..models import Project, Proposal

__all__ = [
    'ProposalForm',
    'ProposalLabelsAdminForm',
    'ProposalLabelsForm',
    'ProposalMoveForm',
    'ProposalTransferForm',
    'ProposalTransitionForm',
]

# FIXME: As labels are user generated content (UGC), these form constructors will
# fail wherever a label's name clashes with a form's default attributes including:
# - csrf_token
# - validate
# - populate_obj
# Do not add UGC field names to a form. Override populate_obj instead


def proposal_label_form(project: Project, proposal: Optional[Proposal]):
    """Return a label form for the given project and proposal."""
    if not project.labels:
        return

    class ProposalLabelForm(forms.Form):
        pass

    for label in project.labels:
        if label.has_options and not label.archived and not label.restricted:
            setattr(
                ProposalLabelForm,
                label.name,
                forms.RadioField(
                    label.form_label_text,
                    description=label.description,
                    validators=(
                        [forms.validators.DataRequired(__("Please select one"))]
                        if label.required
                        else []
                    ),
                    choices=[
                        (option.name, option.title)
                        for option in label.options
                        if not option.archived
                    ],
                ),
            )

    form = ProposalLabelForm(
        obj=proposal.formlabels if proposal is not None else None, meta={'csrf': False}
    )
    del form.form_nonce
    return form


def proposal_label_admin_form(project: Project, proposal: Optional[Proposal]):
    """Return a label form to use in admin panel for given project and proposal."""

    class ProposalLabelAdminForm(forms.Form):
        pass

    for label in project.labels:
        if not label.archived and (label.restricted or not label.has_options):
            form_kwargs = {}
            if label.has_options:
                field_type = forms.RadioField
                form_kwargs['choices'] = [
                    (option.name, option.title)
                    for option in label.options
                    if not option.archived
                ]
            else:
                field_type = forms.BooleanField

            setattr(
                ProposalLabelAdminForm,
                label.name,
                field_type(
                    label.form_label_text,
                    description=label.description,
                    validators=(
                        [forms.validators.DataRequired(__("Please select one"))]
                        if label.required
                        else []
                    ),
                    **form_kwargs,
                ),
            )

    form = ProposalLabelAdminForm(
        obj=proposal.formlabels if proposal is not None else None, meta={'csrf': False}
    )
    del form.form_nonce
    return form


@Proposal.forms('featured')
class ProposalFeaturedForm(forms.Form):
    featured = forms.BooleanField(
        __("Feature this submission"), validators=[forms.validators.InputRequired()]
    )


@Proposal.forms('transfer')
class ProposalTransferForm(forms.Form):
    user = forms.UserSelectField(
        __("Transfer to"),
        description=__("Transfer this submission to another presenter"),
        validators=[forms.validators.DataRequired()],
    )


@Proposal.forms('labels')
class ProposalLabelsForm(forms.Form):
    formlabels = forms.FormField(forms.Form, __("Labels"))

    def set_queries(self):
        self.formlabels.form = proposal_label_form(
            project=self.edit_parent, proposal=self.edit_obj
        )


# FIXME: There is no "admin" in a project anymore. Is this form for editors?
class ProposalLabelsAdminForm(forms.Form):
    formlabels = forms.FormField(forms.Form, __("Labels"))

    def set_queries(self):
        self.formlabels.form = proposal_label_admin_form(
            project=self.edit_parent, proposal=self.edit_obj
        )


@Proposal.forms('main')
class ProposalForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    body = forms.MarkdownField(
        __("Content"), validators=[forms.validators.DataRequired()]
    )
    video_url = forms.URLField(
        __("Video"),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
        description=__("YouTube or Vimeo URL (optional)"),
    )
    formlabels = forms.FormField(forms.Form, __("Labels"))

    def set_queries(self):
        label_form = proposal_label_form(
            project=self.edit_parent, proposal=self.edit_obj
        )
        if label_form is not None:
            self.formlabels.form = label_form
        else:
            del self.formlabels


@Proposal.forms('transition')
class ProposalTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        # value: transition method name
        # label: transition object itself
        # We need the whole object to get the additional metadata in templates
        self.transition.choices = list(self.edit_obj.state.transitions().items())


@Proposal.forms('move')
class ProposalMoveForm(forms.Form):
    target = QuerySelectField(
        __("Move proposal to"),
        description=__("Move this proposal to another project"),
        validators=[forms.validators.DataRequired()],
        get_label='title',
    )

    def set_queries(self):
        self.target.query = current_auth.user.projects_as_editor
