all: assets

assets:
	npm install
	npm run build

build:
	npm run build

babel: babelpy babeljs

babelpy:
	ZXCVBN_DIR=`python -c "import zxcvbn; import pathlib; print(pathlib.Path(zxcvbn.__file__).parent, end='')"`
	pybabel extract -F babel.cfg -k _ -k __ -k ngettext -o funnel/translations/messages.pot . ${ZXCVBN_DIR}
	pybabel update -N -i funnel/translations/messages.pot -d funnel/translations
	pybabel compile -f -d funnel/translations

babeljs: source_dir = funnel/translations
babeljs: target_dir = funnel/static/translations
babeljs: baseframe_dir = $(flask baseframe_translations_path)

babeljs:
	@mkdir -p $(target_dir)
	ls $(source_dir) | grep -E '[[:lower:]]{2}_[[:upper:]]{2}' | xargs -I % sh -c 'mkdir -p $(target_dir)/% && ./node_modules/.bin/po2json --format=jed --pretty $(source_dir)/%/LC_MESSAGES/messages.po $(target_dir)/%/messages.json'
	ls $(baseframe_dir) | grep -E '[[:lower:]]{2}_[[:upper:]]{2}' | xargs -I % sh -c './node_modules/.bin/po2json --format=jed --pretty $(baseframe_dir)/%/LC_MESSAGES/baseframe.po $(target_dir)/%/baseframe.json'
	./node_modules/.bin/prettier --write $(target_dir)/**/**.json

deps: deps-main deps-test deps-dev

deps-main:
	pip-compile --upgrade --output-file=requirements.txt --resolver=backtracking requirements.in

deps-test:
	pip-compile --upgrade --output-file=requirements_test.txt --resolver=backtracking requirements.in requirements_test.in

deps-dev:
	pip-compile --upgrade --output-file=requirements_dev.txt --resolver=backtracking requirements.in requirements_test.in requirements_dev.in

tests-data: tests-data-markdown

tests-data-markdown:
	pytest -v -m update_markdown_data

debug-markdown-tests:
	pytest -v -m debug_markdown_output

tests-bdd:
	pytest --generate-missing --feature tests tests
