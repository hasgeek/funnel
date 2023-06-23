#!/bin/bash

if [ "$(psql -XtA -U postgres -h $DB_HOST $DB_FUNNEL -c "select count(*) from information_schema.tables where table_schema = 'public';")" = "0" ]; then
    flask dbcreate
    flask db stamp
else
    flask db upgrade head
fi
