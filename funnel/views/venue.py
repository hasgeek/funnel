from flask import flash, request

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_redirect
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app, funnelapp
from ..forms.venue import VenueForm, VenuePrimaryForm, VenueRoomForm
from ..models import Project, Venue, VenueRoom, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import ProjectViewMixin, VenueRoomViewMixin, VenueViewMixin

RESERVED_VENUE = ['new']
RESERVED_VENUEROOM = ['new', 'edit', 'delete']


def venue_data(venue):
    return {
        'name': venue.name,
        'title': venue.title,
        'description': venue.description.html,  # FIXME: Needs to be description_html
        'address1': venue.address1,
        'address2': venue.address2,
        'city': venue.city,
        'state': venue.state,
        'postcode': venue.postcode,
        'country': venue.country,
        'latitude': venue.latitude,
        'longitude': venue.longitude,
        'url': None,
        'json_url': None,
    }


def room_data(room):
    return {
        'name': room.scoped_name,
        'title': room.title,
        'description': room.description.html,  # FIXME: Needs to be description_html
        'venue': room.venue.name,
        'bgcolor': room.bgcolor,
        'url': None,
        'json_url': None,
    }


@Project.views('venue')
@route('/<profile>/<project>/venues')
class ProjectVenueView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('venues.html.jinja2')
    @requires_login
    @requires_roles({'editor'})
    def venues(self):
        return {
            'project': self.obj,
            'venues': self.obj.venues,
            'primary_venue_form': VenuePrimaryForm(parent=self.obj),
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_venue(self):
        form = VenueForm()
        if form.validate_on_submit():
            venue = Venue()
            form.populate_obj(venue)
            venue.make_name(reserved=RESERVED_VENUE)
            self.obj.venues.append(venue)
            if not self.obj.primary_venue:
                self.obj.primary_venue = venue
            db.session.commit()
            flash(_("You have added a new venue to the event"), 'success')
            return render_redirect(self.obj.url_for('venues'), code=303)
        return render_form(
            form=form,
            title=_("New venue"),
            submit=_("Add venue"),
            cancel_url=self.obj.url_for('venues'),
            ajax=False,
        )

    @route('update_venue_settings', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'editor'})
    def update_venue_settings(self):
        if request.json is None:
            return {'error': _("Invalid data")}, 400
        for venue_uuid_b58 in request.json.keys():
            venue = Venue.query.filter_by(uuid_b58=venue_uuid_b58).first()
            if venue is not None:
                venue.seq = request.json[venue_uuid_b58]['seq']
                db.session.add(venue)
                for room in request.json[venue_uuid_b58]['rooms']:
                    room_obj = VenueRoom.query.filter_by(
                        uuid_b58=room['uuid_b58'], venue=venue
                    ).first()
                    if room_obj is not None:
                        room_obj.bgcolor = room['color'].lstrip('#')
                        room_obj.seq = room['seq']
                        db.session.add(room_obj)
        try:
            db.session.commit()
            return {'status': True}
        except Exception as e:
            return {'error': str(e)}, 400

    @route('makeprimary', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def makeprimary_venue(self):
        form = VenuePrimaryForm(parent=self.obj)
        if form.validate_on_submit():
            venue = form.venue.data
            if venue == self.obj.primary_venue:
                flash(_("This is already the primary venue"), 'info')
            else:
                self.obj.primary_venue = venue
                db.session.commit()
                flash(_("You have changed the primary venue"), 'success')
        else:
            flash(_("Please select a venue"), 'danger')
        return render_redirect(self.obj.url_for('venues'), code=303)


@route('/<project>/venues', subdomain='<profile>')
class FunnelProjectVenueView(ProjectVenueView):
    pass


ProjectVenueView.init_app(app)
FunnelProjectVenueView.init_app(funnelapp)


@Venue.views('main')
@route('/<profile>/<project>/venues/<venue>')
class VenueView(VenueViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def edit(self):
        form = VenueForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            self.obj.make_name(reserved=RESERVED_VENUE)
            db.session.commit()
            flash(_("Saved changes to this venue"), 'success')
            return render_redirect(self.obj.project.url_for('venues'), code=303)
        return render_form(
            form=form,
            title=_("Edit venue"),
            submit=_("Save"),
            cancel_url=self.obj.project.url_for('venues'),
            ajax=False,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title="Confirm delete",
            message=_(
                "Delete venue “{title}”? This cannot be undone".format(
                    title=self.obj.title
                )
            ),
            success=_("You have deleted venue “{title}”".format(title=self.obj.title)),
            next=self.obj.project.url_for('venues'),
        )

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def new_venueroom(self):
        form = VenueRoomForm()
        if form.validate_on_submit():
            room = VenueRoom()
            form.populate_obj(room)
            room.make_name(reserved=RESERVED_VENUEROOM)
            self.obj.rooms.append(room)
            db.session.commit()
            flash(_("You have added a room at this venue"), 'success')
            return render_redirect(self.obj.project.url_for('venues'), code=303)
        return render_form(
            form=form,
            title=_("New room"),
            submit=_("Create"),
            cancel_url=self.obj.project.url_for('venues'),
            ajax=False,
        )


@route('/<project>/venues/<venue>', subdomain='<profile>')
class FunnelVenueView(VenueView):
    pass


VenueView.init_app(app)
FunnelVenueView.init_app(funnelapp)


@VenueRoom.views('main')
@route('/<profile>/<project>/venues/<venue>/<room>')
class VenueRoomView(VenueRoomViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def edit(self):
        form = VenueRoomForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            self.obj.make_name(reserved=RESERVED_VENUEROOM)
            db.session.commit()
            flash(_("Saved changes to this room"), 'success')
            return render_redirect(self.obj.venue.project.url_for('venues'), code=303)
        return render_form(
            form=form,
            title=_("Edit room"),
            submit=_("Save"),
            cancel_url=self.obj.venue.project.url_for('venues'),
            ajax=False,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title="Confirm delete",
            message=_(
                "Delete room “{title}”? This cannot be undone".format(
                    title=self.obj.title
                )
            ),
            success=_("You have deleted room “{title}”".format(title=self.obj.title)),
            next=self.obj.venue.project.url_for('venues'),
        )


@route('/<project>/venues/<venue>/<room>', subdomain='<profile>')
class FunnelVenueRoomView(VenueRoomView):
    pass


VenueRoomView.init_app(app)
FunnelVenueRoomView.init_app(funnelapp)
