from flask import request
from flask_socketio import Namespace, emit, join_room, leave_room

from baseframe import _
from coaster.auth import current_auth

from .. import app, socketio


class ModelUpdates(Namespace):
    """
    Sends notifications to clients when an object is updated.

    This test implementation only sends publicly accessible data, so is not suitable
    for access-protected views. Expected use case is for reporting new comments in
    a real-time feed.

    SocketIO recognises "namespaces" and "rooms", with the expectation that namespaces
    represent the various parts of an app, and rooms are channels for updating everyone
    in that room. Here we use the "/updates" namespace and treat every instance of
    every model as a distinct room using the naming syntax "table_name/uuid_b58". We
    could also treat a page as a room, so that any update to any component of a page
    will trigger a push to the room.

    Either approach requires tracking of the components included in a page. In our
    current architecture, the server does not know these components as views are
    imperative and not declarative. It is not possible to examine a view and determine
    what it will return. The client, however, has the page and knows what components are
    in it.

    Sometimes the server may also have new information, such as a new comment on a
    project. In this case, the client must specifically subscribe to a journal on the
    parent, asking for information on descendents of a specific type.

    https://stackoverflow.com/questions/10930286/socket-io-rooms-or-namespacing
    """

    def on_connect(self):
        emit('chatter', _("Socket connected"))
        app.logger.debug(
            "Socket connection from user %r with sid %r",
            current_auth.actor,
            request.sid,
        )

    def on_disconnect(self):
        app.logger.debug(
            "Socket disconnected by user %r with sid %r",
            current_auth.actor,
            request.sid,
        )

    # Client sends:
    # 1. Track changes: socket.emit('track', {model: 'model', uuid_b58: 'id'});
    # 2. Get journal: socket.emit('track', {model: 'model', uuid_b58: 'id', type: 'comment'});
    def on_track(self, message):
        if 'type' in message:
            join_room(
                '%s/%s/%s' % (message['model'], message['uuid_b58'], message['type'])
            )
        else:
            join_room('%s/%s' % (message['model'], message['uuid_b58']))

    # Client sends socket.emit('untrack', {model: 'model', uuid_b58: 'id'});
    # This happens when the client is reloading the page and no longer wants to
    # track the objects it was previously tracking
    def on_untrack(self, message):
        if 'type' in message:
            leave_room(
                '%s/%s/%s' % (message['model'], message['uuid_b58'], message['type'])
            )
        else:
            leave_room('%s/%s' % (message['model'], message['uuid_b58']))


socketio.on_namespace(ModelUpdates('/updates'))
