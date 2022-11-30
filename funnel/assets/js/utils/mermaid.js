const MermaidEmbed = {
  addMermaid() {
    $('.language-mermaid').each(function embedMarkmap() {
      $(this).addClass('embed-added');
      $(this).find('code').addClass('mermaid');
    });
    window.mermaid.initialize({ startOnLoad: true });
  },
  loadMermaid() {
    const self = this;
    if (!window.mermaid) {
      $.ajax({
        url: 'https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js',
        dataType: 'script',
        cache: true,
      }).done(() => {
        self.addMermaid();
      });
    } else {
      self.addMermaid();
    }
  },
  init() {
    if ($('.language-mermaid').length > 0) {
      this.loadMermaid();
    }
  },
};

export default MermaidEmbed;
