const MarkmapEmbed = {
  addMarkmap() {
    const self = this;
    self.container
      .find('.md-embed-markmap:not(.activating):not(.activated)')
      .each(function embedMarkmap() {
        $(this).find('.embed-loading').html('Loading mindmap&mldr;');
        $(this).addClass('activating');
        const current = $(this).find('.embed-container');
        current
          .addClass('markmap')
          .append(
            `<script type="text/template">${$(this)
              .find('.embed-content')
              .text()}</script>`
          );
        window.markmap.autoLoader.renderAllUnder(this);
        $(this).addClass('activated').removeClass('activating');
      });
  },
  resizeTimer: null,
  resizeMarkmapContainers() {
    const debounceInterval = 500;
    if (this.resizeTimer) clearTimeout(this.resizeTimer);
    this.resizeTimer = setTimeout(() => {
      $('.md-embed-markmap.activated svg').each(function mmresized() {
        const circles = $(this).find('circle');
        const firstNode = circles[circles.length - 1];
        firstNode.dispatchEvent(new Event('click'));
        firstNode.dispatchEvent(new Event('click'));
      });
    }, debounceInterval);
  },
  loadMarkmap() {
    const self = this;
    const CDN = [
      'https://cdn.jsdelivr.net/npm/d3@6',
      'https://cdn.jsdelivr.net/npm/markmap-view',
      'https://cdn.jsdelivr.net/npm/markmap-autoloader',
    ];
    let asset = 0;
    const loadMarkmapScript = () => {
      $.ajax({
        url: CDN[asset],
        dataType: 'script',
        cache: true,
      }).done(() => {
        if (asset < CDN.length - 1) {
          asset += 1;
          if (window.markmap) {
            window.markmap = {
              autoLoader: {
                manual: true,
                onReady: () => {
                  window.markmap.Markmap.defaultOptions = {
                    ...window.markmap.Markmap.defaultOptions,
                    autoFit: true,
                    pan: false,
                    fitRatio: 0.85,
                    initialExpandLevel: 1,
                  };
                },
              },
            };
          }
          loadMarkmapScript();
        } else {
          self.addMarkmap();
          window.addEventListener('resize', this.resizeMarkmapContainers.bind(this));
        }
      });
    };
    if (!window.markmap) {
      loadMarkmapScript();
    } else {
      self.addMarkmap();
    }
  },
  init(container) {
    this.container = $(container || 'body');
    if (
      this.container.find('.md-embed-markmap:not(.activated):not(.activated)').length >
      0
    ) {
      this.loadMarkmap();
    }
  },
};

export default MarkmapEmbed;
