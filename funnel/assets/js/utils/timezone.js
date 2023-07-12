import 'jquery.cookie';

// Detect timezone for login
async function setTimezoneCookie() {
  if (!$.cookie('timezone')) {
    let timezone = Intl.DateTimeFormat()?.resolvedOptions()?.timeZone;
    if (!timezone) {
      const { default: jstz } = await import('jstz');
      timezone = jstz.determine().name();
    }
    $.cookie('timezone', timezone, { path: '/' });
  }
}

export default setTimezoneCookie;
