from baseframe import __
from baseframe.forms.sqlalchemy import QuerySelectField
from coaster.auth import current_auth
import baseframe.forms as forms

from ..models import Proposal

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


def proposal_label_form(project, proposal):
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
        obj=proposal.formlabels if proposal else None, meta={'csrf': False}
    )
    del form.form_nonce
    return form


def proposal_label_admin_form(project, proposal):
    """
    Returns a label form to use in admin panel for given project and proposal
    """

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
        obj=proposal.formlabels if proposal else None, meta={'csrf': False}
    )
    del form.form_nonce
    return form


@Proposal.forms('transfer')
class ProposalTransferForm(forms.Form):
    user = forms.UserSelectField(
        __("Transfer to"),
        description=__("Transfer this proposal to another speaker"),
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
    speaking = forms.RadioField(
        __("Are you speaking?"),
        coerce=int,
        choices=[
            (1, __("I will be speaking")),
            (0, __("I’m proposing a topic for someone to speak on")),
        ],
    )
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
        description=__("The title of your session"),
    )
    abstract = forms.MarkdownField(
        __("Abstract"),
        validators=[forms.validators.DataRequired()],
        description=__(
            "A brief description of your session with target audience and key takeaways"
        ),
    )
    outline = forms.MarkdownField(
        __("Outline"),
        validators=[forms.validators.DataRequired()],
        description=__(
            "A detailed description of the session with the sequence of ideas to be presented"
        ),
    )
    requirements = forms.MarkdownField(
        __("Requirements"),
        description=__("For workshops, what must participants bring to the session?"),
    )
    slides = forms.URLField(
        __("Slides"),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
        description=__(
            "Link to your slides. These can be just an outline initially. "
            "If you provide a Slideshare/Speakerdeck link, we'll embed slides in the page"
        ),
    )
    video_url = forms.URLField(
        __("Preview Video"),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
        description=__(
            "Link to your preview video. Use a video to engage the community and give them a better "
            "idea about what you are planning to cover in your session and why they should attend. "
            "If you provide a YouTube/Vimeo link, we'll embed it in the page"
        ),
    )
    links = forms.TextAreaField(
        __("Links"),
        description=__(
            "Other links, one per line. Provide links to your profile and "
            "slides and videos from your previous sessions; anything that'll help "
            "folks decide if they want to attend your session"
        ),
    )
    bio = forms.MarkdownField(
        __("Speaker bio"),
        validators=[forms.validators.DataRequired()],
        description=__("Tell us why you are the best person to be taking this session"),
    )
    email = forms.EmailField(
        __("Your email address"),
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
        description=__(
            "An email address we can contact you at. " "Not displayed anywhere"
        ),
    )
    phone = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        description=__(
            "A phone number we can call you at to discuss your proposal, if required. "
            "Will not be displayed"
        ),
    )
    location = forms.StringField(
        __("Your location"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        description=__("Your location, to help plan for your travel if required"),
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
        """
        value: transition method name
        label: transition object itself
        We need the whole object to get the additional metadata in templates
        """
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
