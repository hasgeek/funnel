#! /usr/bin/env python

from coaster.manage import init_manager

from funnel import funnelapp, app, models


if __name__ == "__main__":
    manager = init_manager(app, models.db)
    manager.run()
