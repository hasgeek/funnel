const MermaidEmbed = {
  addMermaid() {
    const self = this;
    let idCount = $('.md-embed-mermaid.activating, .md-embed-mermaid.activated').length;
    const idMarker = 'mermaid_elem_';
    const instances = self.container.find(
      '.md-embed-mermaid:not(.activating):not(.activated)'
    );
    instances.each(function embedMarkmap() {
      const root = $(this);
      root.addClass('activating');
      const contentElem = root.find('.embed-content');
      const containerElem = root.find('.embed-container');
      const definition = contentElem.text();
      let elemId = containerElem.attr('id');
      if (!elemId) {
        elemId = `${idMarker}${idCount}`;
        do {
          idCount += 1;
        } while ($(`#${idMarker}${idCount}`).length > 0);
      }
      window.mermaid.render(elemId, definition, (svg) => {
        containerElem.html(svg);
        root.addClass('activated').removeClass('activating');
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
  init(container) {
    this.container = $(container || 'body');
    if (
      this.container.find('.md-embed-mermaid:not(.activating):not(.activated)').length >
      0
    ) {
      this.loadMermaid();
    }
  },
};

export default MermaidEmbed;
