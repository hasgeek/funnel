const MarkmapEmbed = {
  addMarkmap() {
    $('.language-markmap').each(function embedMarkmap() {
      $(this).addClass('embed-added');
      $(this).find('code').addClass('markmap');
      $(this).after(
        $(
          '<div>Click the empty white connectors <strong>&#9675;</strong> to close/collapse a node &amp; the filled coloured connectors <strong>&#9679;</strong> to open/expand a node.</div>'
        ).addClass('embed-caption')
      );
    });
    window.markmap.autoLoader.renderAll();
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
        }
      });
    };
    if (!window.markmap) {
      loadMarkmapScript();
    } else {
      self.addMarkmap();
    }
  },
  init(containerDiv) {
    this.containerDiv = containerDiv;
    if ($('.language-markmap').length > 0) {
      this.loadMarkmap();
    }
  },
};

export default MarkmapEmbed;
