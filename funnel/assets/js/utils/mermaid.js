const MermaidEmbed = {
  addMermaid() {
    const instances = $('.md-embed-mermaid:not(.activating):not(.activated)');
    let idCount = $('.md-embed-mermaid.activating, .md-embed-mermaid.activated').length;
    const idMarker = 'mermaid_elem_';
    instances.each(function embedMarkmap() {
      const root = $(this);
      root.addClass('activating');
      const elem = root.find('.embed-content');
      const definition = elem.text();
      let elemId = elem.attr('id');
      if (!elemId) {
        elemId = `${idMarker}${idCount}`;
        do {
          idCount += 1;
        } while ($(`#${idMarker}${idCount}`).length > 0);
      }
      window.mermaid.render(elemId, definition, (svg) => {
        elem.html(svg);
        root.addClass('activated');
        root.removeClass('activating');
      });
    });
  },
  loadMermaid() {
    const self = this;
    if (!window.mermaid) {
      $.ajax({
        url: 'https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js',
        dataType: 'script',
        cache: true,
      }).done(() => {
        window.mermaid.initialize({ startOnLoad: false });
        self.addMermaid();
      });
    } else {
      self.addMermaid();
    }
  },
  init() {
    if ($('.md-embed-mermaid:not(.activated)').length > 0) {
      this.loadMermaid();
    }
  },
};

export default MermaidEmbed;
