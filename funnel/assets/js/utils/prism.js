const PrismEmbed = {
  activatePrism() {
    $('code[class*=language-]:not(.activated):not(.activating)').each(
      function activate() {
        window.Prism.highlightElement(this);
      }
    );
  },
  hooked: false,
  loadPrism() {
    const CDN_CSS = 'https://unpkg.com/prismjs/themes/prism.min.css';
    const CDN = [
      'https://unpkg.com/prismjs/components/prism-core.min.js',
      'https://unpkg.com/prismjs/plugins/autoloader/prism-autoloader.min.js',
    ];
    let asset = 0;
    const loadPrismStyle = () => {
      if (!$(`link[href*="${CDN_CSS}"]`).length)
        $('head').append($(`<link href="${CDN_CSS}" rel="stylesheet"></link>`));
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
            window.Prism.hooks.add('before-sanity-check', (env) => {
              if (env.element) $(env.element).addClass('activating');
            });
            window.Prism.hooks.add('complete', (env) => {
              if (env.element)
                $(env.element).addClass('activated').removeClass('activating');
            });
            this.hooked = true;
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
  init(containerDiv) {
    this.containerDiv = containerDiv;
    if ($('code[class*=language-]:not(.activated):not(.activating)').length > 0) {
      this.loadPrism();
    }
  },
};

export default PrismEmbed;
