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

class Gettext {
  constructor(messagesJson) {
    this.domain = messagesJson.domain;
    this.config = messagesJson.locale_data.messages[''];
    delete messagesJson.locale_data.messages[''];
    this.catalog = messagesJson.locale_data.messages;
  }

  gettext(msgid, ...args) {
    if (msgid in this.catalog) {
      var msgidCatalog = this.catalog[msgid];

      if (msgidCatalog.length < 2) {
        console.error(
          'Invalid format for translated messages, at least 2 values expected'
        );
      }
      // in case of gettext() first element is empty because it's the msgid_plural,
      // and the second element is the translated msgstr
      var msgstr = msgidCatalog[1];
      if (args.length > 0) {
        for (var i = 0; i < args.length; i = i + 1) {
          msgstr = msgstr.replace('%d', args[i]);
        }
      }
      return msgstr;
    } else {
      return msgid;
    }
  }

  ngettext(msgid, msgidPlural, num) {
    if (msgid in this.catalog) {
      var msgidCatalog = this.catalog[msgid];

      if (msgidCatalog.length < 3) {
        console.error(
          'Invalid format for translated messages, at least 3 values expected for plural translations'
        );
      }

      if (msgidPlural !== msgidCatalog[0]) {
        console.error("Plural forms don't match");
      }

      if (num <= 1) {
        return msgidCatalog[1].replace('%d', num);
      } else {
        return msgidCatalog[2].replace('%d', num);
      }
    } else {
      return msgid;
    }
  }
}

$(() => {
  window.Hasgeek.Gettext = Gettext;
});
