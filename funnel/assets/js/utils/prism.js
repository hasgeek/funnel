const PrismEmbed = {
  activatePrism() {
    const activator = window.Prism.hooks.all.complete[0] || null;
    if (activator) {
      $('code[class*=language-]:not(.activated)').each(function activate() {
        const languages = this.className
          .split(' ')
          .filter((cls) => cls.startsWith('language-'));
        const language = languages[0].replace('language-', '') || null;
        if (language) {
          activator({ element: this, language });
          this.classList.add('activated');
        }
      });
    }
  },
  loadPrism() {
    const CDN_CSS = 'https://unpkg.com/prismjs/themes/prism.min.css';
    const CDN = [
      'https://unpkg.com/prismjs/components/prism-core.min.js',
      'https://unpkg.com/prismjs/plugins/autoloader/prism-autoloader.min.js',
    ];
    let asset = 0;
    const loadPrismStyle = () => {
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
        } else this.activatePrism();
      });
    };
    if (!window.Prism) {
      loadPrismStyle();
      loadPrismScript();
    }
  },
  init(containerDiv) {
    this.containerDiv = containerDiv;
    if ($('code[class*=language-]:not(.activated)').length > 0) {
      this.loadPrism();
    }
  },
};

export default PrismEmbed;
