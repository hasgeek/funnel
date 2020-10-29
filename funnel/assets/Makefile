all: assets

assets:
	npm install
	npm run build

assetsonly:
	npm run build

babel:
	find ../translations -iname '*.po' | xargs -I % sh -c './node_modules/.bin/po2json --pretty % `dirname %`/`basename % .po`.json'
