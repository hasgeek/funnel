// Hasgeek Gettext
// ---------------
// A cheap implementation that works on JSON generated from .po files
// using po2json, specifically using `jed` format.

// gettext ref: https://www.gnu.org/software/gettext/manual/html_node/Translating-plural-forms.html
// message format in .po files in case of singular -

// white-space
// #  translator-comments
// #. extracted-comments
// #: reference…
// #, flag…
// #| msgctxt previous-context
// #| msgid previous-untranslated-string
// msgctxt context
// msgid untranslated-string
// msgstr translated-string

// which is shown in the JSON in this format -

// "msgid": [
//   null,
//   "msgstr"
// ],

// for plural

// white-space
// #  translator-comments
// #. extracted-comments
// #: reference…
// #, flag…
// #| msgid previous-untranslated-string-singular
// #| msgid_plural previous-untranslated-string-plural
// msgid untranslated-string-singular
// msgid_plural untranslated-string-plural
// msgstr[0] translated-string-case-0
// ...
// msgstr[N] translated-string-case-n

// Such an entry can look like this:

// #: src/msgcmp.c:338 src/po-lex.c:699
// #, c-format
// msgid "%d new message"
// msgid_plural "%d new messages"
// msgstr[0] "%d नया संदेश"
// msgstr[1] "%d नए संदेश"

// and in JSON -

// "msgid": [
//   "msgid_plural",
//   "msgstr[0]",  // in case of singular
//   "msgstr[1]",  // in case of plural
// ],

var sprintf = require('sprintf-js').sprintf,
  vsprintf = require('sprintf-js').vsprintf;

const Gettext = function (messagesJson) {
  let config = {
    domain: 'messages',
    locale_data: {
      messages: {},
    },
  };
  config = messagesJson || config;
  this.domain = config.domain;
  this.catalog = config.locale_data.messages;

  this.gettext = function (msgid, ...args) {
    if (msgid in this.catalog) {
      let msgidCatalog = this.catalog[msgid];

      if (msgidCatalog.length < 2) {
        console.error(
          'Invalid format for translated messages, at least 2 values expected'
        );
      }
      // in case of gettext() first element is empty because it's the msgid_plural,
      // and the second element is the translated msgstr
      return vsprintf(msgidCatalog[1], args);
    } else {
      return vsprintf(msgid, args);
    }
  };

  this.ngettext = function (msgid, msgidPlural, num, ...args) {
    if (msgid in this.catalog) {
      let msgidCatalog = this.catalog[msgid];

      if (msgidCatalog.length < 3) {
        console.error(
          'Invalid format for translated messages, at least 3 values expected for plural translations'
        );
      }

      if (msgidPlural !== msgidCatalog[0]) {
        console.error("Plural forms don't match");
      }

      let msgstr = '';
      if (num <= 1) {
        msgstr = sprintf(msgidCatalog[1], { num: num });
      } else {
        msgstr = sprintf(msgidCatalog[2], { num: num });
      }
      return vsprintf(msgstr, args);
    } else {
      return vsprintf(msgid, args);
    }
  };
};

module.exports = Gettext;
