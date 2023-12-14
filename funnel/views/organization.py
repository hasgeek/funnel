"""Views for organizations."""

from __future__ import annotations

from flask import abort, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_message
from coaster.auth import current_auth
from coaster.views import ModelView, UrlChangeCheck, UrlForView, requires_roles, route

from .. import app
from ..forms import OrganizationForm, TeamForm
from ..models import Account, Organization, Team, db
from ..signals import org_data_changed, team_data_changed
from ..typing import ReturnView
from .helpers import render_redirect
from .login_session import requires_login, requires_sudo, requires_user_not_spammy

# --- Routes: Organizations ---------------------------------------------------


@Organization.views()
def people_and_teams(obj: Organization) -> list[tuple[Account, list[Team]]]:
    """Extract a list of users from the org's public teams."""
    # This depends on user.member_teams not using lazy='dynamic'. When that changes, we
    # will need a different approach to match users to teams. Comparison is by id rather
    # than by object because teams are loaded separately in the two queries, and
    # SQLAlchemy's session management doesn't merge the instances.
    teams = [team for team in obj.teams if team.is_public]
    result = [
        (
            user,
            [
                team
                for team in teams
                if team.id in (uteam.id for uteam in user.member_teams)
            ],
        )
        for user in obj.people()
    ]
    return result


@Account.views('org')
@route('/<account>', init_app=app)
class OrgView(UrlChangeCheck, UrlForView, ModelView[Account]):
    """Views for organizations."""

    __decorators__ = [requires_login]
    # Map <account> in URL to attribute `urlname`, for `url_for` automation
    route_model_map = {'account': 'urlname'}

    def load(self, account: str | None = None) -> None:
        """Load an organization if the view requires it."""
        if account:
            obj = Account.get(name=account)
            if obj is None:
                abort(404)
            if not obj.state.ACTIVE:
                abort(410)
            self.obj = obj

    # The /new root URL is intentional
    @route('/new', methods=['GET', 'POST'], endpoint='new_organization')
    @requires_user_not_spammy()
    def new(self) -> ReturnView:
        """Create a new organization."""
        form = OrganizationForm(edit_user=current_auth.user)
        if form.validate_on_submit():
            org = Organization(owner=current_auth.user)
            form.populate_obj(org)
            db.session.add(org)
            org.make_profile_public()
            db.session.commit()
            org_data_changed.send(org, changes=['new'], user=current_auth.user)
            return render_redirect(org.url_for('edit'))
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
        if self.obj.is_protected:
            return render_message(
                title=_("Protected account"),
                message=_(
                    "This organization is marked as protected and cannot be deleted"
                ),
            )
        if not self.obj.is_safe_to_delete():
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
            cancel_url=self.obj.url_for(),
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
            team = Team(account=self.obj)
            db.session.add(team)
            form.populate_obj(team)
            db.session.commit()
            team_data_changed.send(team, changes=['new'], user=current_auth.user)
            return render_redirect(self.obj.url_for('teams'))
        return render_form(
            form=form, title=_("Create new team"), formid='new_team', submit=_("Create")
        )


@Team.views('main')
@route('/<account>/teams/<team>', init_app=app)
class TeamView(UrlChangeCheck, UrlForView, ModelView[Team]):
    """Views for teams in organizations."""

    __decorators__ = [requires_login]
    # Map <name> and <buid> in URLs to model attributes, for `url_for` automation
    route_model_map = {
        'account': 'account.urlname',
        'team': 'buid',
    }

    def loader(self, account: str, team: str) -> Team:
        """Load a team."""
        obj = Team.get(buid=team, with_parent=True)
        if obj is None or obj.account.urlname != account:
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
            return render_redirect(self.obj.account.url_for('teams'))
        return render_form(
            form=form,
            title=_("Edit team: {title}").format(title=self.obj.title),
            formid='team_edit',
            submit=_("Save"),
            cancel_url=self.obj.account.url_for('teams'),
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
            ).format(team=self.obj.title, org=self.obj.account.title),
            next=self.obj.account.url_for('teams'),
        )
