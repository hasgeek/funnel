function updateParsleyConfig() {
  // Override Parsley.js's default messages after the page loads.
  // Our versions don't use full stops after phrases.
  window.ParsleyConfig = {
    errorsWrapper: '<div></div>',
    errorTemplate: '<p class="mui-form__error"></p>',
    errorClass: 'has-error',
    classHandler(ParsleyField) {
      return ParsleyField.$element.closest('.mui-form__fields');
    },
    errorsContainer(ParsleyField) {
      return ParsleyField.$element.closest('.mui-form__controls');
    },
    i18n: {
      en: {},
    },
  };

  window.ParsleyConfig.i18n.en = $.extend(window.ParsleyConfig.i18n.en || {}, {
    defaultMessage: 'This value seems to be invalid',
    notblank: 'This value should not be blank',
    required: 'This value is required',
    pattern: 'This value seems to be invalid',
    min: 'This value should be greater than or equal to %s',
    max: 'This value should be lower than or equal to %s',
    range: 'This value should be between %s and %s',
    minlength: 'This value is too short. It should have %s characters or more',
    maxlength: 'This value is too long. It should have %s characters or fewer',
    length: 'This value should be between %s and %s characters long',
    mincheck: 'You must select at least %s choices',
    maxcheck: 'You must select %s choices or fewer',
    check: 'You must select between %s and %s choices',
    equalto: 'This value should be the same',
  });

  window.ParsleyConfig.i18n.en.type = $.extend(
    window.ParsleyConfig.i18n.en.type || {},
    {
      email: 'This value should be a valid email',
      url: 'This value should be a valid url',
      number: 'This value should be a valid number',
      integer: 'This value should be a valid integer',
      digits: 'This value should be digits',
      alphanum: 'This value should be alphanumeric',
    }
  );
}

export default updateParsleyConfig;
