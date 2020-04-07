#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lastuser_core.models import AuthClient, Organization, User  # isort:skip
from lastuserapp import app, db

# incase data exists from previously run tests
db.drop_all()
# create schema again
db.create_all()

# Add fixtures for test app
# user for CRUD workflow: creating client app
gustav = User(
    username="gustav", fullname="Gustav 'world' Dachshund", password='worldismyball'
)

# org for associating with client
# client for CRUD workflow of defining perms *in* client
# spare user for CRUD workflow of assigning permissions
oakley = User(username="oakley", fullname="Oakley 'huh' Dachshund")
dachsunited = Organization(name="dachsunited", title="Dachs United")
dachsunited.owners.users.append(gustav)
dachshundworld = AuthClient(
    title="Dachshund World",
    org=dachsunited,
    confidential=True,
    website="http://gustavsdachshundworld.com",
)

db.session.add(gustav)
db.session.add(oakley)
db.session.add(dachsunited)
db.session.add(dachshundworld)
db.session.commit()

app.run('0.0.0.0')
