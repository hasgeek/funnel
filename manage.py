#! /usr/bin/env python
# -*- coding: utf-8 -*-

from coaster.manage import Manager, init_manager
from funnel import app, funnelapp, lastuserapp, models

periodic = Manager(usage="Periodic tasks from cron (with recommended intervals)")


@periodic.command
def phoneclaims():
    """Sweep phone claims to close all unclaimed beyond expiry period (10m)"""
    models.UserPhoneClaim.delete_expired()
    models.db.session.commit()


if __name__ == "__main__":
    manager = init_manager(
        app, models.db, models=models, funnelapp=funnelapp, lastuserapp=lastuserapp
    )
    manager.add_command('periodic', periodic)
    manager.run()
