#! /usr/bin/env python

from coaster.manage import init_manager

from website import app, models, init_for


if __name__ == "__main__":
    manager = init_manager(app, models.db, init_for)
    manager.run()
