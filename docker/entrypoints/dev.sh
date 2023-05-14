#!/bin/bash

npm install
make deps-editable
pip install --upgrade pip
pip install --use-pep517 -r requirements/dev.txt

if [ $(psql -XtA -U postgres -h postgres funnel -c "select count(*) from information_schema.tables where table_schema = 'public';") = "0" ]; then
    flask dbcreate
    flask db stamp
else
    echo "Tables exist"
fi

flask db upgrade head

./devserver.py
