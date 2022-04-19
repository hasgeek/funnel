from __future__ import annotations

from typing import Optional

from flask import flash, render_template, request

from baseframe import _
from baseframe.forms import render_redirect
from baseframe.forms.auto import ConfirmDeleteForm
from coaster.auth import current_auth
from coaster.views import ModelView, UrlChangeCheck, UrlForView, route

from .. import app
from ..forms import ProjectSponsorForm
from ..models import Profile, Project, SponsorMembership, db
from .login_session import requires_login, requires_site_editor
from .mixins import ProjectViewMixin


def edit_sponsor_form(obj):
    """Customise ProjectSponsorForm to remove profile field."""
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
    def add_sponsor(self):
        form = ProjectSponsorForm()

        if request.method == 'POST':
            if form.validate_on_submit():
                existing_sponsorship = SponsorMembership.query.filter(
                    SponsorMembership.is_active,
                    SponsorMembership.project == self.obj,
                    SponsorMembership.profile == form.profile.data,
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
                else:
                    sponsor_membership = SponsorMembership(
                        project=self.obj,
                        granted_by=current_auth.user,
                    )
                    form.populate_obj(sponsor_membership)
                    db.session.add(sponsor_membership)
                    db.session.commit()
                    flash(_("Sponsor has been added"), 'info')
                    return render_redirect(self.obj.url_for())

            else:
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
            'add_sponsor_modal.html.jinja2',
            project=self.obj,
            form=form,
            action=self.obj.url_for('add_sponsor'),
            ref_id='add_sponsor',
        )


ProjectSponsorLandingView.init_app(app)


@SponsorMembership.views('main')
@route('/<profile>/<project>/sponsors/<sponsorship>')
class ProjectSponsorView(UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [requires_login, requires_site_editor]
    model = SponsorMembership
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
    ) -> SponsorMembership:
        return (
            self.model.query.join(Project, Profile)
            .filter(self.model.uuid_b58 == sponsorship, self.model.is_active)
            .one_or_404()
        )

    @route('edit', methods=['GET', "POST"])
    def edit(self):
        sponsorship = self.obj
        form = edit_sponsor_form(sponsorship)
        if request.method == 'POST':
            if form.validate_on_submit():
                with db.session.no_autoflush:
                    with sponsorship.amend_by(current_auth.user) as amendment:
                        form.populate_obj(amendment)
                    sponsorship = amendment.membership
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
            'add_sponsor_modal.html.jinja2',
            project=self.obj.project,
            form=form,
            action=sponsorship.url_for('edit'),
            ref_id='edit_sponsor',
            sponsorship=sponsorship,
        )

    @route('remove', methods=['GET', "POST"])
    def remove(self):
        form = ConfirmDeleteForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                self.obj.revoke(actor=current_auth.user)
                db.session.commit()
                flash(_("Sponsor has been removed"), 'info')
                return render_redirect(self.obj.project.url_for())
            else:
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
            'add_sponsor_modal.html.jinja2',
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
