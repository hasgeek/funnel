from __future__ import annotations

from typing import Optional

from flask import abort, flash, redirect, render_template, request, url_for

from baseframe import _
from baseframe.forms import (
    render_delete_sqla,
    render_form,
    render_message,
    render_redirect,
)
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    get_next_url,
    requires_roles,
    route,
)

from .. import app
from ..forms import OrganizationForm, TeamForm
from ..models import Organization, Team, db
from ..signals import org_data_changed, team_data_changed
from ..typing import ReturnView
from .login_session import requires_login, requires_sudo

# --- Routes: Organizations ---------------------------------------------------


@Organization.views('people_and_teams')
def people_and_teams(obj):
    """Extract a list of users from the org's public teams."""
    # This depends on user.teams not using lazy='dynamic'. When that changes, we will
    # need a different approach to match users to teams. Comparison is by id rather
    # than by object because teams are loaded separately in the two queries, and
    # SQLAlchemy's session management doesn't merge the instances.
    teams = [team for team in obj.teams if team.is_public]
    result = [
        (
            user,
            [team for team in teams if team.id in (uteam.id for uteam in user.teams)],
        )
        for user in obj.people()
    ]
    return result


@Organization.views('main')
@route('/<organization>')
class OrgView(UrlChangeCheck, UrlForView, ModelView):
    """Views for organizations."""

    __decorators__ = [requires_login]
    model = Organization
    # Map <organization> in URL to attribute `name`, for `url_for` automation
    route_model_map = {'organization': 'name'}
    obj: Organization

    def loader(self, organization: Optional[str] = None) -> Optional[Organization]:
        """Load an organization if the view requires it."""
        if organization:
            obj = Organization.get(name=organization)
            if obj is None:
                abort(404)
            return obj
        return None

    # The /new root URL is intentional
    @route('/new', methods=['GET', 'POST'])
    def new(self) -> ReturnView:
        """Create a new organization."""
        if not current_auth.user.has_verified_contact_info:
            flash(
                _(
                    "You need to have a verified email address"
                    " or phone number to create an organization"
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

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'owner'})
    def delete(self) -> ReturnView:
        """Delete organization if safe to do so."""
        if self.obj.profile.is_protected:
            return render_message(
                title=_("Protected profile"),
                message=_(
                    "This organization has a protected profile and cannot be deleted"
                ),
            )
        if not self.obj.profile.is_safe_to_delete():
            return render_message(
                title=_("This organization has projects"),
                message=_(
                    "Projects must be deleted or transferred before the organization"
                    " can be deleted"
                ),
            )

        if request.method == 'POST':
            # FIXME: Find a better way to do this
            org_data_changed.send(self.obj, changes=['delete'], user=current_auth.user)
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete organization ‘{title}’? This will delete everything including"
                " projects, proposals and videos. This operation is permanent and"
                " cannot be undone"
            ).format(title=self.obj.title),
            success=_(
                "You have deleted organization ‘{title}’ and all its associated content"
            ).format(title=self.obj.title),
            next=url_for('account'),
            cancel_url=self.obj.profile.url_for(),
        )

    @route('teams')
    @requires_roles({'admin'})
    def teams(self) -> ReturnView:
        """Render list of teams."""
        return render_template('organization_teams.html.jinja2', org=self.obj)

    @route('teams/new', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def new_team(self) -> ReturnView:
        """Create a new team."""
        form = TeamForm()
        if form.validate_on_submit():
            team = Team(organization=self.obj)
            db.session.add(team)
            form.populate_obj(team)
            db.session.commit()
            team_data_changed.send(team, changes=['new'], user=current_auth.user)
            return render_redirect(self.obj.url_for('teams'), code=303)
        return render_form(
            form=form, title=_("Create new team"), formid='new_team', submit=_("Create")
        )


OrgView.init_app(app)


@Team.views('main')
@route('/<organization>/teams/<team>')
class TeamView(UrlChangeCheck, UrlForView, ModelView):
    """Views for teams in organizations."""

    __decorators__ = [requires_login]
    model = Team
    # Map <name> and <buid> in URLs to model attributes, for `url_for` automation
    route_model_map = {
        'organization': 'organization.name',
        'team': 'buid',
    }
    obj: Team

    def loader(self, organization: str, team: str) -> Team:
        """Load a team."""
        obj = Team.get(buid=team, with_parent=True)
        if obj is None or obj.organization.name != organization:
            abort(404)
        return obj

    @route('', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit(self) -> ReturnView:
        """Edit team."""
        form = TeamForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            team_data_changed.send(self.obj, changes=['edit'], user=current_auth.user)
            return render_redirect(self.obj.organization.url_for('teams'), code=303)
        return render_form(
            form=form,
            title=_("Edit team: {title}").format(title=self.obj.title),
            formid='team_edit',
            submit=_("Save"),
            cancel_url=self.obj.organization.url_for('teams'),
            ajax=False,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'admin'})
    def delete(self) -> ReturnView:
        """Delete team."""
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
            next=self.obj.organization.url_for('teams'),
        )


TeamView.init_app(app)
