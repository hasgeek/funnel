all:
	cd funnel/assets; make

build:
	cd funnel/assets; make assetsonly

babel:
	ZXCVBN_DIR=`python -c "import zxcvbn; import pathlib; print(pathlib.Path(zxcvbn.__file__).parent, end='')"`
	pybabel extract -F babel.cfg -k _ -k __ -k ngettext -o funnel/translations/messages.pot . ${ZXCVBN_DIR}
	pybabel update -N -i funnel/translations/messages.pot -d funnel/translations
	pybabel compile -f -d funnel/translations
	cd funnel/assets; make babel

deps: deps-main deps-dev deps-test

deps-main:
	pip-compile --upgrade requirements.in

deps-dev:
	pip-compile --upgrade requirements_dev.in

deps-test:
	pip-compile --upgrade requirements_test.in
