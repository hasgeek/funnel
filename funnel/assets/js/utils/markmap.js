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
    const markmapEmbed = this;
    if (
      parentElement.find('.md-embed-markmap:not(.activating):not(.activated)').length >
      0
    ) {
      const { Transformer } = await import('markmap-lib');
      const { Markmap } = await import('markmap-view');
      const transformer = new Transformer();

      parentElement
        .find('.md-embed-markmap:not(.activating):not(.activated)')
        .each(function embedMarkmap() {
          const markdownDiv = this;
          $(markdownDiv).addClass('activating');
          $(markdownDiv).find('.embed-loading').addClass('loading');
          const { root } = transformer.transform(
            $(markdownDiv).find('.embed-content').text()
          );
          $(markdownDiv).find('.embed-container').append('<svg></svg>');
          const current = $(markdownDiv).find('svg')[0];
          const markmap = Markmap.create(current, null, root);
          markmapEmbed.markmaps.push(markmap);
          $(markdownDiv).addClass('activated').removeClass('activating');
        });

      window.addEventListener('resize', this.resizeMarkmapContainers.bind(this));
    }
  },
};

export default MarkmapEmbed;
