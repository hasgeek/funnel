import Prism from 'prismjs';
import 'prismjs/plugins/autoloader/prism-autoloader';
import 'prismjs/plugins/match-braces/prism-match-braces';
import 'prismjs/plugins/toolbar/prism-toolbar';
import 'prismjs/plugins/show-language/prism-show-language';
import 'prismjs/plugins/copy-to-clipboard/prism-copy-to-clipboard';

Prism.plugins.autoloader.languages_path = '/static/build/js/prismjs/components/';

const PrismEmbed = {
  activatePrism() {
    this.container
      .find('code[class*=language-]:not(.activated):not(.activating)')
      .each(function activate() {
        Prism.highlightElement(this);
      });
  },
  init(container) {
    this.container = $(container || 'body');
    if (
      this.container.find('code[class*=language-]:not(.activated):not(.activating)')
        .length > 0
    ) {
      Prism.hooks.add('before-sanity-check', (env) => {
        if (env.element) $(env.element).addClass('activating');
      });
      Prism.hooks.add('complete', (env) => {
        if (env.element) $(env.element).addClass('activated').removeClass('activating');
        $(env.element)
          .parent()
          .parent()
          .find('.toolbar-item')
          .find('a, button')
          .addClass('mui-btn mui-btn--accent mui-btn--raised mui-btn--small');
      });
      $('body').addClass('match-braces').addClass('rainbow-braces');
      this.activatePrism();
    }
  },
};

export default PrismEmbed;
