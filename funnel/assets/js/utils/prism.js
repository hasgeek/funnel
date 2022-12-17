const PrismEmbed = {
  activatePrism() {
    this.container
      .find('code[class*=language-]:not(.activated):not(.activating)')
      .each(function activate() {
        window.Prism.highlightElement(this);
      });
  },
  hooked: false,
  loadPrism() {
    const CDN_CSS = [
      'https://unpkg.com/prismjs/themes/prism.min.css',
      'https://unpkg.com/prismjs/plugins/line-numbers/prism-line-numbers.min.css',
      'https://unpkg.com/prismjs/plugins/match-braces/prism-match-braces.min.css',
      'https://unpkg.com/prismjs/plugins/toolbar/prism-toolbar.min.css',
    ];
    const CDN = [
      'https://unpkg.com/prismjs/components/prism-core.min.js',
      'https://unpkg.com/prismjs/plugins/autoloader/prism-autoloader.min.js',
      'https://unpkg.com/prismjs/plugins/match-braces/prism-match-braces.min.js',
      'https://unpkg.com/prismjs/plugins/line-numbers/prism-line-numbers.min.js',
      'https://unpkg.com/prismjs/plugins/toolbar/prism-toolbar.min.js',
      'https://unpkg.com/prismjs/plugins/show-language/prism-show-language.min.js',
      'https://unpkg.com/prismjs/plugins/copy-to-clipboard/prism-copy-to-clipboard.min.js',
    ];
    let asset = 0;
    const loadPrismStyle = () => {
      for (let i = 0; i < CDN_CSS.length; i += 1) {
        if (!$(`link[href*="${CDN_CSS[i]}"]`).length)
          $('head').append($(`<link href="${CDN_CSS[i]}" rel="stylesheet"></link>`));
      }
    };
    const loadPrismScript = () => {
      $.ajax({
        url: CDN[asset],
        dataType: 'script',
        cache: true,
      }).done(() => {
        if (asset < CDN.length - 1) {
          asset += 1;
          loadPrismScript();
        } else {
          if (!this.hooked) {
            this.hooked = true;
            window.Prism.hooks.add('before-sanity-check', (env) => {
              if (env.element) $(env.element).addClass('activating');
            });
            window.Prism.hooks.add('complete', (env) => {
              if (env.element)
                $(env.element).addClass('activated').removeClass('activating');
            });
            $('body')
              .addClass('line-numbers')
              .addClass('match-braces')
              .addClass('rainbow-braces');
          }
          this.activatePrism();
        }
      });
    };
    loadPrismStyle();
    if (!window.Prism) {
      loadPrismScript();
    } else this.activatePrism();
  },
  init(container) {
    this.container = $(container || 'body');
    if (
      this.container.find('code[class*=language-]:not(.activated):not(.activating)')
        .length > 0
    ) {
      this.loadPrism();
    }
  },
};

export default PrismEmbed;
