all:
	@echo "You must have an active Python virtualenv (3.7+) before using any of these."
	@echo
	@echo "For production deployment:"
	@echo "  make install       # For first time setup and after dependency upgrades"
	@echo "  make assets        # For only Node asset changes"
	@echo
	@echo "For testing and CI:"
	@echo "  make install-test  # Install everything needed for a test environment"
	@echo
	@echo "For development:"
	@echo "  make install-dev   # For first time setup and after dependency upgrades"
	@echo "  make deps          # Scan for dependency upgrades (and test afterwards!)"
	@echo "  make deps-python   # Scan for Python dependency upgrades"
	@echo "  make deps-npm      # Scan for NPM dependency upgrades"
	@echo
	@echo "To upgrade dependencies in a development environment, use all in order and"
	@echo "commit changes only if all tests pass:"
	@echo
	@echo "  make deps"
	@echo "  make install-dev"
	@echo "  pytest"

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

babel: babelpy babeljs

deps-editable: DEPS = coaster baseframe
deps-editable:
	@if [ ! -d "build" ]; then mkdir build; fi;
	@if [ ! -d "build/dependencies" ]; then mkdir build/dependencies; fi;
	@cd build/dependencies;\
	for dep in $(DEPS); do\
		if [ -e "$$dep" ]; then\
			echo "Updating $$dep...";\
			echo `cd $$dep;git pull;`;\
		else\
			echo "Cloning dependency $$dep as locally editable installation...";\
			git clone https://github.com/hasgeek/$$dep.git;\
		fi;\
	done;

deps-python: deps-editable
	pip-compile-multi --backtracking --use-cache

deps-python-rebuild: deps-editable
	pip-compile-multi --backtracking

deps-python-base: deps-editable
	pip-compile-multi -t requirements/base.in --backtracking --use-cache

deps-python-test: deps-editable
	pip-compile-multi -t requirements/test.in --backtracking --use-cache

deps-python-dev: deps-editable
	pip-compile-multi -t requirements/dev.in --backtracking --use-cache

deps-python-verify:
	pip-compile-multi verify

deps-npm:
	npm update

deps: deps-python deps-npm

install-npm:
	npm install

install-npm-ci:
	npm clean-install

install-python-pip:
	pip install --upgrade pip setuptools

install-python-dev: install-python-pip deps-editable
	pip install -r requirements/dev.txt

install-python-test: install-python-pip deps-editable
	pip install -r requirements/test.txt --no-deps

install-python: install-python-pip deps-editable
	pip install -r requirements/base.txt

install-dev: deps-editable install-python-dev install-npm assets

install-test: deps-editable install-python-test install-npm-ci assets

install: deps-editable install-python install-npm-ci assets

assets:
	npm run build

debug-markdown-tests:
	pytest -v -m debug_markdown_output

tests-bdd:
	pytest --generate-missing --feature tests tests
