all:
	cd funnel/assets; make

build:
	cd funnel/assets; make assetsonly

babel:
	pybabel extract -F babel.cfg -k _ -k __ -k ngettext -o funnel/translations/messages.pot .
	pybabel update -N -i funnel/translations/messages.pot -d funnel/translations
	pybabel compile -f -d funnel/translations
	cd funnel/assets; make babel
