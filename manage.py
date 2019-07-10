#! /usr/bin/env python

from coaster.manage import init_manager
from funnel import app, funnelapp, models

if __name__ == "__main__":
    models.db.app = app
    manager = init_manager(app, models.db, models=models, funnelapp=funnelapp)
    manager.run()
