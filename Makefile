ifeq ($(shell test -d .venv/bin && echo 1 || echo 0), 1)
    export PATH := .venv/bin:$(PATH)
endif

all:
	@echo "You must have an active Python virtualenv (3.11+) before using any of these."
	@echo
	@echo "For production deployment:"
	@echo
	@echo "  make install       # For first time setup and after dependency upgrades"
	@echo "  make assets        # For only Node asset changes"
	@echo
	@echo "For testing and CI:"
	@echo
	@echo "  make install-test  # Install everything needed for a test environment"
	@echo "  make install-playwright  # Install browsers for Playwright-based tests"
	@echo
	@echo "For development:"
	@echo
	@echo "  make install-dev   # For first time setup and after dependency upgrades"
	@echo "  make deps-noup     # Rebuild for dependency changes, but skip upgrades"
	@echo "  make deps          # Scan for dependency upgrades (remember to test!)"
	@echo "  make deps-python   # Scan for Python dependency upgrades"
	@echo "  make deps-npm      # Scan for NPM dependency upgrades"
	@echo
	@echo "To export a new symbol from any Python file, regenerate '__init__.py' files:"
	@echo
	@echo "  make initpy"
	@echo
	@echo "After editing any UI strings, regenerate Babel translation databases:"
	@echo
	@echo "  make babel"
	@echo
	@echo "To upgrade dependencies in a development environment, use all in order and"
	@echo "commit changes only if all tests pass:"
	@echo
	@echo "  make deps"
	@echo "  make install-dev"
	@echo "  pytest"

babelpy:
	ZXCVBN_DIR=`python -c "import zxcvbn; import pathlib; print(pathlib.Path(zxcvbn.__file__).parent, end='')"`
	pybabel extract -F babel.cfg -k _ -k __ -k _n -k __n -k gettext -k ngettext -o funnel/translations/messages.pot funnel ${ZXCVBN_DIR}
	pybabel update -N -i funnel/translations/messages.pot -d funnel/translations
	pybabel compile -f -d funnel/translations

babeljs: source_dir = funnel/translations
babeljs: target_dir = funnel/static/translations
babeljs: baseframe_dir = $(flask baseframe_translations_path)

babeljs:
	@mkdir -p $(target_dir)
	ls $(source_dir) | grep -E '[[:lower:]]{2}_[[:upper:]]{2}' | xargs -I % sh -c 'mkdir -p $(target_dir)/% && ./node_modules/.bin/po2json --format=jed --pretty --domain=messages $(source_dir)/%/LC_MESSAGES/messages.po $(target_dir)/%/messages.json'
	ls $(baseframe_dir) | grep -E '[[:lower:]]{2}_[[:upper:]]{2}' | xargs -I % sh -c './node_modules/.bin/po2json --format=jed --pretty --domain=baseframe $(baseframe_dir)/%/LC_MESSAGES/baseframe.po $(target_dir)/%/baseframe.json'
	./node_modules/.bin/prettier --write $(target_dir)/**/**.json

babel: babelpy babeljs

docker-bases: docker-base docker-base-devtest

docker-base:
	docker buildx build -f docker/images/bases.Dockerfile --target base --tag hasgeek/funnel-base .

docker-base-devtest:
	docker buildx build -f docker/images/bases.Dockerfile --target base-devtest --tag hasgeek/funnel-base-devtest .

docker-ci-test:
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain \
	docker compose --profile test up --quiet-pull --no-attach db-test --no-attach redis-test --no-log-prefix

docker-dev:
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 \
	docker compose --profile dev up --abort-on-container-exit --build --force-recreate --no-attach db-dev --no-attach redis-dev --remove-orphans

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
	pip install --upgrade pip pip-tools pip-compile-multi
	pip-compile-multi --backtracking --use-cache

deps-python-noup:
	pip-compile-multi --backtracking --use-cache --no-upgrade

deps-python-rebuild: deps-editable
	pip-compile-multi --backtracking --live

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

deps-noup: deps-python-noup

deps: deps-python deps-npm

initpy: initpy-models initpy-forms initpy-loginproviders initpy-transports initpy-utils

initpy-models:
	mkinit --inplace --relative --black --lazy_loader_typed funnel/models/__init__.py
	isort funnel/models/__init__.py funnel/models/__init__.pyi
	black funnel/models/__init__.py funnel/models/__init__.pyi

initpy-forms:
	mkinit --inplace --relative --black funnel/forms/__init__.py
	isort funnel/forms/__init__.py
	black funnel/forms/__init__.py

initpy-loginproviders:
	mkinit --inplace --relative --black funnel/loginproviders/__init__.py
	isort funnel/loginproviders/__init__.py
	black funnel/loginproviders/__init__.py

initpy-transports:
	# Do not auto-gen funnel/transports/__init__.py, only sub-packages
	mkinit --inplace --relative --black funnel/transports/email
	mkinit --inplace --relative --black funnel/transports/sms
	isort funnel/transports/*/__init__.py
	black funnel/transports/*/__init__.py

initpy-utils:
	mkinit --inplace --relative --black --recursive funnel/utils
	isort funnel/utils/__init__.py funnel/utils/*/__init__.py funnel/utils/*/*/__init__.py
	black funnel/utils/__init__.py funnel/utils/*/__init__.py funnel/utils/*/*/__init__.py

install-npm:
	npm install

install-npm-ci:
	npm clean-install

install-python-pip:
	pip install --upgrade pip

install-python-dev: install-python-pip deps-editable
	pip install --use-pep517 -r requirements/dev.txt

install-python-test: install-python-pip deps-editable
	pip install --use-pep517 -r requirements/test.txt

install-python: install-python-pip deps-editable
	pip install --use-pep517 -r requirements/base.txt

install-playwright:
	@if command -v playwright > /dev/null; then\
		echo "playwright install --with-deps";\
		playwright install --with-deps;\
	else\
		echo "Install Playwright first: make install-python-test";\
		exit 1;\
	fi

install-dev: deps-editable install-python-dev install-playwright install-npm assets

install-test: deps-editable install-python-test install-playwright install-npm assets

install: deps-editable install-python install-npm-ci assets

assets:
	npm run build

assets-dev:
	npm run build-dev

debug-markdown-tests:
	pytest -v -m debug_markdown_output

tests-bdd:
	pytest --generate-missing --feature tests tests
