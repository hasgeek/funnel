all: assets

assets: deps-nodejs build

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

deps: deps-python deps-nodejs

deps-python: deps-install
	pip-compile-multi --backtracking --use-cache

deps-python-no-cache: deps-install
	pip-compile-multi --backtracking

deps-python-base: deps-install
	pip-compile-multi -t requirements/base.in --backtracking --use-cache

deps-python-test:
	pip-compile-multi -t requirements/test.in --backtracking --use-cache

deps-python-dev: deps-python

deps-python-verify:
	pip-compile-multi verify

deps-nodejs:
	npm run install

deps-install: DEPS = coaster baseframe
deps-install:
	@if [ ! -d ".dependencies" ]; then mkdir .dependencies; fi;
	@cd .dependencies;\
	for dep in $(DEPS); do\
		if [ -e "$$dep" ]; then\
			echo "Dependency $$dep already loaded. Updating $$dep...";\
			echo `cd $$dep;git pull;`;\
		else\
			echo "Dependency $$dep not loaded. Fetching $$dep...";\
			git clone https://github.com/hasgeek/$$dep.git;\
		fi;\
	done;

install-dev: deps-install
	pip install -r requirements/dev.txt
install-test: deps-install
	pip install -r requirements/test.txt
install: deps-install
	pip install -r requirements/base.txt


debug-markdown-tests:
	pytest -v -m debug_markdown_output
