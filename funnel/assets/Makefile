all: assets

assets:
	npm install
	npm run build

assetsonly:
	npm run build

source_dir = ../translations
target_dir = ../static/translations/

babel:
	mkdir -p $(target_dir)
	ls $(source_dir) | grep _ | xargs -I % sh -c 'mkdir -p $(target_dir)/% && ./node_modules/.bin/po2json --pretty $(source_dir)/%/LC_MESSAGES/messages.po $(target_dir)/%/messages.json'
	# List locales ----^^^^^^ (e.g. hi_IN)
