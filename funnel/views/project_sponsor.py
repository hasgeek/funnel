"""Views for managing sponsors of a project."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from flask import abort, flash, render_template, request

from baseframe import _
from baseframe.forms import Form
from baseframe.forms.auto import ConfirmDeleteForm
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import ModelView, UrlChangeCheck, UrlForView, requestform, route

from .. import app
from ..forms import ProjectSponsorForm
from ..models import Profile, Project, ProjectSponsorMembership, db, sa
from ..typing import ReturnView
from .helpers import render_redirect
from .login_session import requires_login, requires_site_editor
from .mixins import ProjectViewMixin


def edit_sponsor_form(obj):
    """Customise ProjectSponsorForm to remove account field."""
    form = ProjectSponsorForm(obj=obj)
    del form.profile
    return form


@Project.views('sponsors')
@route('/<profile>/<project>/')
class ProjectSponsorLandingView(
    ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView
):
    __decorators__ = [requires_login, requires_site_editor]

    @route('sponsors/add', methods=['POST', 'GET'])
    def add_sponsor(self) -> ReturnView:
        form = ProjectSponsorForm()

        if request.method == 'POST':
            if form.validate_on_submit():
                if TYPE_CHECKING:
                    assert isinstance(form.profile.data, Profile)  # nosec
                existing_sponsorship = ProjectSponsorMembership.query.filter(
                    ProjectSponsorMembership.is_active,
                    ProjectSponsorMembership.project == self.obj,
                    ProjectSponsorMembership.profile == form.profile.data,
                ).one_or_none()
                if existing_sponsorship is not None:
                    return (
                        {
                            'status': 'error',
                            'error_description': _(
                                "{sponsor} is already a sponsor"
                            ).format(sponsor=form.profile.data.pickername),
                            'errors': form.errors,
                            'form_nonce': form.form_nonce.data,
                        },
                        400,
                    )
                sponsor_membership = ProjectSponsorMembership(
                    project=self.obj,
                    granted_by=current_auth.user,
                )
                form.populate_obj(sponsor_membership)
                db.session.add(sponsor_membership)
                db.session.commit()
                flash(_("Sponsor has been added"), 'info')
                return render_redirect(self.obj.url_for())
            return (
                {
                    'status': 'error',
                    'error_description': _("Sponsor could not be added"),
                    'errors': form.errors,
                    'form_nonce': form.form_nonce.data,
                },
                400,
            )
        return render_template(
            'project_sponsor_popup.html.jinja2',
            project=self.obj,
            form=form,
            action=self.obj.url_for('add_sponsor'),
            ref_id='add_sponsor',
        )

    @route('sponsors/reorder', methods=['POST'])
    @requestform('target', 'other', ('before', getbool))
    def reorder_sponsors(self, target: str, other: str, before: bool) -> ReturnView:
        if not (current_auth.user and current_auth.user.is_site_editor):
            abort(403)
        if Form().validate_on_submit():
            sponsor: ProjectSponsorMembership = (
                ProjectSponsorMembership.query.filter_by(uuid_b58=target)
                .options(
                    sa.orm.load_only(
                        ProjectSponsorMembership.id, ProjectSponsorMembership.seq
                    )
                )
                .one_or_404()
            )
            other_sponsor: ProjectSponsorMembership = (
                ProjectSponsorMembership.query.filter_by(uuid_b58=other)
                .options(
                    sa.orm.load_only(
                        ProjectSponsorMembership.id, ProjectSponsorMembership.seq
                    )
                )
                .one_or_404()
            )
            sponsor.reorder_item(other_sponsor, before)
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'csrf'}, 422


ProjectSponsorLandingView.init_app(app)


@ProjectSponsorMembership.views('main')
@route('/<profile>/<project>/sponsors/<sponsorship>')
class ProjectSponsorView(UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [requires_login, requires_site_editor]
    model = ProjectSponsorMembership
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'sponsorship': 'uuid_b58',
    }

    def loader(
        self,
        profile: str,  # skipcq: PYL-W0613
        project: str,  # skipcq: PYL-W0613
        sponsorship: Optional[str] = None,
    ) -> ProjectSponsorMembership:
        obj = (
            self.model.query.join(Project)
            .join(Profile)
            .filter(self.model.uuid_b58 == sponsorship)
            .one_or_404()
        )
        if not obj.is_active:
            abort(410)
        return obj

    @route('edit', methods=['GET', "POST"])
    def edit(self) -> ReturnView:
        form = edit_sponsor_form(self.obj)
        if request.method == 'POST':
            if form.validate_on_submit():
                with db.session.no_autoflush:
                    with self.obj.amend_by(current_auth.user) as amendment:
                        form.populate_obj(amendment)
                    db.session.commit()
                    flash(_("Sponsor has been edited"), 'info')
                    return render_redirect(self.obj.project.url_for())

            else:
                return (
                    {
                        'status': 'error',
                        'error_description': _("Sponsor could not be edited"),
                        'errors': form.errors,
                        'form_nonce': form.form_nonce.data,
                    },
                    400,
                )
        return render_template(
            'project_sponsor_popup.html.jinja2',
            project=self.obj.project,
            form=form,
            action=self.obj.url_for('edit'),
            ref_id='edit_sponsor',
            sponsorship=self.obj,
        )

    @route('remove', methods=['GET', "POST"])
    def remove(self) -> ReturnView:
        form = ConfirmDeleteForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                self.obj.revoke(actor=current_auth.user)
                db.session.commit()
                flash(_("Sponsor has been removed"), 'info')
                return render_redirect(self.obj.project.url_for())

            return (
                {
                    'status': 'error',
                    'error_description': _("Sponsor could not be removed"),
                    'errors': form.errors,
                    'form_nonce': form.form_nonce.data,
                },
                400,
            )

        return render_template(
            'project_sponsor_popup.html.jinja2',
            form=form,
            title="Remove sponsor?",
            message=_("Remove ‘{sponsor}’ as a sponsor?").format(
                sponsor=self.obj.profile.title
            ),
            action=self.obj.url_for('remove'),
            ref_id='remove_sponsor',
            remove=True,
        )


ProjectSponsorView.init_app(app)
