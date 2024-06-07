const MarkmapEmbed = {
  resizeTimer: null,
  markmaps: [],
  resizeMarkmapContainers() {
    const debounceInterval = 500;
    if (this.resizeTimer) clearTimeout(this.resizeTimer);
    this.resizeTimer = setTimeout(() => {
      this.markmaps.forEach((markmap) => {
        markmap.fit();
      });
    }, debounceInterval);
  },
  async init(container) {
    const parentElement = $(container || 'body');
    const self = this;
    if (
      parentElement.find('.md-embed-markmap:not(.activating, .activated)').length > 0
    ) {
      const { Transformer } = await import('markmap-lib');
      const { Markmap } = await import('markmap-view');
      const transformer = new Transformer();

      const observer = new IntersectionObserver(
        (items) => {
          items.forEach((item) => {
            if (item.isIntersecting) $(item.target).data('markmap').fit();
          });
        },
        {
          root: $('.main-content')[0],
        },
      );

      parentElement
        .find('.md-embed-markmap:not(.activating):not(.activated)')
        .each(function embedMarkmap() {
          $(this).addClass('activating');
          $(this).find('.embed-loading').addClass('loading');
          const { root } = transformer.transform($(this).find('.embed-content').text());
          $(this).find('.embed-container').append('<svg></svg>');
          const current = $(this).find('svg')[0];
          const markmap = Markmap.create(
            current,
            {
              autoFit: true,
              pan: false,
              fitRatio: 0.85,
              initialExpandLevel: 1,
            },
            root,
          );
          self.markmaps.push(markmap);
          $(current).data('markmap', markmap);
          observer.observe(current);
          $(this).addClass('activated').removeClass('activating');
        });

      window.addEventListener('resize', this.resizeMarkmapContainers.bind(this));
    }
  },
};

export default MarkmapEmbed;
