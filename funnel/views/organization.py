from flask import abort, flash, redirect, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_redirect
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlForView,
    get_next_url,
    requires_permission,
    route,
)

from .. import app
from ..forms import OrganizationForm, TeamForm
from ..models import Organization, Team, db
from ..signals import org_data_changed, team_data_changed
from .helpers import requires_login

# --- Routes: Organizations ---------------------------------------------------


@Organization.views('main')
@route('/organizations')
class OrgView(UrlForView, ModelView):
    __decorators__ = [requires_login]
    model = Organization
    # Map <organization> in URL to attribute `name`, for `url_for` automation
    route_model_map = {'organization': 'name'}

    def loader(self, organization=None):
        if organization:
            obj = Organization.get(name=organization)
            if not obj:
                abort(404)
            return obj

    @route('', endpoint='organization_list')
    def index(self):
        return render_template(
            'organization_index.html.jinja2',
            organizations=current_auth.user.organizations_as_owner,
        )

    @route('/new', methods=['GET', 'POST'])
    def new(self):
        if not current_auth.user.has_verified_contact_info:
            flash(
                _(
                    "You need to have a verified email address "
                    "or phone number to create an organization"
                ),
                'error',
            )
            return redirect(get_next_url(referrer=True), code=303)

        form = OrganizationForm()
        if form.validate_on_submit():
            org = Organization(owner=current_auth.user)
            form.populate_obj(org)
            db.session.add(org)
            org.profile.make_public()
            db.session.commit()
            org_data_changed.send(org, changes=['new'], user=current_auth.user)
            return render_redirect(org.profile.url_for('edit'), code=303)
        return render_form(
            form=form,
            title=_("Create a new organization"),
            formid='org_new',
            submit=_("Next"),
            ajax=False,
        )

    # TODO: Deprecated, redirect user to /<profile> instead once teams are removed
    @route('<organization>')
    @requires_permission('view')
    def view(self):
        return render_template('organization.html.jinja2', org=self.obj)

    # TODO: Deprecated, use `/<profile>/edit` instead
    @route('<organization>/edit', methods=['GET', 'POST'])
    @requires_permission('edit')
    def edit(self):
        form = OrganizationForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            org_data_changed.send(self.obj, changes=['edit'], user=current_auth.user)
            return render_redirect(self.obj.url_for('view'), code=303)
        return render_form(
            form=form,
            title=_("Edit organization"),
            formid='org_edit',
            submit=_("Save"),
            ajax=False,
        )

    # The /root URL is intentional as profiles don't have a delete endpoint
    @route('/<organization>/delete', methods=['GET', 'POST'])
    @requires_permission('delete')
    def delete(self):
        if request.method == 'POST':
            # FIXME: Find a better way to do this
            org_data_changed.send(self.obj, changes=['delete'], user=current_auth.user)
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_("Delete organization ‘{title}’? ").format(title=self.obj.title),
            success=_(
                "You have deleted organization ‘{title}’ and all its associated teams"
            ).format(title=self.obj.title),
            next=url_for('OrgView_index'),
        )

    @route('<organization>/teams')
    @requires_permission('view-teams')
    def teams(self):
        # There's no separate teams page at the moment
        return redirect(self.obj.url_for('view'))

    @route('<organization>/teams/new', methods=['GET', 'POST'])
    @requires_permission('new-team')
    def new_team(self):
        form = TeamForm()
        if form.validate_on_submit():
            team = Team(organization=self.obj)
            db.session.add(team)
            form.populate_obj(team)
            db.session.commit()
            team_data_changed.send(team, changes=['new'], user=current_auth.user)
            return render_redirect(self.obj.url_for('view'), code=303)
        return render_form(
            form=form, title=_("Create new team"), formid='new_team', submit=_("Create")
        )


OrgView.init_app(app)


@Team.views('main')
@route('/organizations/<organization>/teams/<team>')
class TeamView(UrlForView, ModelView):
    __decorators__ = [requires_login]
    model = Team
    route_model_map = {  # Map <name> and <buid> in URLs to model attributes, for `url_for` automation
        'organization': 'organization.name',
        'team': 'buid',
    }

    def loader(self, organization, team):
        obj = Team.get(buid=team, with_parent=True)
        if not obj or obj.organization.name != organization:
            abort(404)
        return obj

    @route('', methods=['GET', 'POST'])
    @requires_permission('edit')
    def edit(self):
        form = TeamForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            team_data_changed.send(self.obj, changes=['edit'], user=current_auth.user)
            return render_redirect(self.obj.organization.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Edit team: {title}").format(title=self.obj.title),
            formid='team_edit',
            submit=_("Save"),
            ajax=False,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_permission('delete')
    def delete(self):
        if request.method == 'POST':
            team_data_changed.send(self.obj, changes=['delete'], user=current_auth.user)
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_("Delete team {title}?").format(title=self.obj.title),
            success=_(
                "You have deleted team ‘{team}’ from organization ‘{org}’"
            ).format(team=self.obj.title, org=self.obj.organization.title),
            next=self.obj.organization.url_for(),
        )


TeamView.init_app(app)
