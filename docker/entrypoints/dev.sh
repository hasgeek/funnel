#!/bin/bash

if [ "$(psql -XtA -U postgres -h "$DB_HOST" funnel -c "select count(*) from information_schema.tables where table_schema = 'public';")" = "0" ]; then
    flask dbcreate
    flask db stamp
fi

./devserver.py
