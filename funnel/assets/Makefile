all: assets

assets:
	npm install
	npm run build

assetsonly:
	npm run build

babel:
	mkdir -p ../static/translations
	find ../translations -iname '*.po' | xargs -I % sh -c './node_modules/.bin/po2json --pretty % ../static/translations/`basename % .po`.json'
