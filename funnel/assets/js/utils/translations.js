import Gettext from './gettext';

function getLocale() {
  // Instantiate i18n with browser context
  const { lang } = document.documentElement;
  const langShortForm = lang.substring(0, 2);
  window.Hasgeek.Config.locale =
    window.Hasgeek.Config.availableLanguages[langShortForm];
  return window.Hasgeek.Config.locale;
}

function loadLangTranslations() {
  getLocale();

  window.i18n = new Gettext({
    translatedLang: window.Hasgeek.Config.locale,
  });
  window.gettext = window.i18n.gettext.bind(window.i18n);
  window.ngettext = window.i18n.ngettext.bind(window.i18n);
}

export default loadLangTranslations;
