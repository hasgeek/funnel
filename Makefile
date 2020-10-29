all:
	cd funnel/assets; make

build:
	cd funnel/assets; make assetsonly

babel:
	pybabel extract -F babel.cfg -k _ -k __ -k ngettext -o funnel/translations/messages.pot .
	pybabel update -D funnel -i funnel/translations/messages.pot -d funnel/translations
	cd funnel/assets; make babel
