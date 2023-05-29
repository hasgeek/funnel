"""Additional sample configuration for production."""

# Matomo analytics
MATOMO_URL = ''
MATOMO_ID = '1'
MATOMO_JS = 'stats.js'
MATOMO_FILE = 'stats.php'

#: Google Analytics code UA-XXXXXX-X
GA_CODE = ''

#: Google site verification code
GOOGLE_SITE_VERIFICATION = ''

#: GeoIP Config
GEOIP_DB_CITY = '/path/to/GeoLite2-City.mmdb'
GEOIP_DB_ASN = '/path/to/GeoLite2-ASN.mmdb'

SMS_VERIFICATION_TEMPLATE = ''

#: Telegram statistics bot
TELEGRAM_STATS_APIKEY = TELEGRAM_STATS_BOT_TOKEN = ''  # nosec
TELEGRAM_STATS_CHATID = TELEGRAM_STATS_CHAT_ID = ''  # nosec

TELEGRAM_ERROR_APIKEY = ''
TELEGRAM_ERROR_CHATID = ''
