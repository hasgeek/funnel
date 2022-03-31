from __future__ import annotations

from flask import abort, flash, render_template

from baseframe import _
from baseframe.forms import render_redirect
from baseframe.forms.auto import ConfirmDeleteForm
from coaster.auth import current_auth
from coaster.views import ModelView, UrlChangeCheck, UrlForView, route

from .. import app
from ..forms import AddSponsorForm
from ..models import Profile, Project, SponsorMembership, db
from .login_session import requires_login


@SponsorMembership.views('main')
@route('/<profile>/<project>/sponsors/<sponsor>')
class ProjectSponsorView(UrlChangeCheck, UrlForView, ModelView):
    model = SponsorMembership
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'sponsor': 'id',
    }

    AddSponsorForm = AddSponsorForm

    def loader(
        self,
        profile: str,  # skipcq: PYL-W0613
        project: str,  # skipcq: PYL-W0613
        sponsor: str,
    ) -> SponsorMembership:
        obj = (
            self.model.query.join(Project, Profile)
            .filter(SponsorMembership.id == sponsor)
            .first()
        )

        return obj

    def after_loader(self):
        self.project = self.obj.project
        self.profile = self.obj.profile
        return super().after_loader()

    @route('edit', methods=['GET', "POST"])
    @requires_login
    def edit_sponsor(self):
        if not current_auth.user.is_site_editor:
            abort(403)
        sponsorship = self.obj
        form = AddSponsorForm(
            label=self.obj.label, is_promoted=self.obj.is_promoted, obj=sponsorship
        )
        form.profile.data = [self.profile.name]

        if form.validate_on_submit():
            del form.profile
            with db.session.no_autoflush:
                with sponsorship.amend_by(current_auth.user) as amendment:
                    form.populate_obj(amendment)
            db.session.commit()
            flash(_("Sponsor has been edited"), 'info')
            return render_redirect(self.project.url_for())

        return render_template(
            'add_sponsor_modal.html.jinja2',
            project=self.project,
            form=form,
            action=self.obj.url_for('edit_sponsor'),
            ref_id='edit_sponsor',
            sponsorship=sponsorship,
        )

    @route('remove', methods=['GET', "POST"])
    @requires_login
    def remove_sponsor(self):
        if not current_auth.user.is_site_editor:
            abort(403)
        sponsorship = self.obj
        user = current_auth.user

        form = ConfirmDeleteForm()
        sponsor_name = self.obj.profile.name
        if form.validate_on_submit():
            sponsorship.revoke(actor=user)
            db.session.add(sponsorship)
            db.session.commit()
            flash(_("Sponsor has been removed"), 'info')
            return render_redirect(self.project.url_for())

        return render_template(
            'add_sponsor_modal.html.jinja2',
            form=form,
            title="Remove Sponsor?",
            message=("Do you want to remove ‘{sponsor_name}’ as a sponsor?").format(
                sponsor_name=sponsor_name
            ),
            action=self.obj.url_for('remove_sponsor'),
            ref_id='remove_sponsor',
            remove=True,
        )


ProjectSponsorView.init_app(app)
