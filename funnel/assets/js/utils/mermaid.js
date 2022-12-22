async function addMermaidEmbed(container) {
  const parentElement = $(container || 'body');
  if (
    parentElement.find('.md-embed-mermaid:not(.activating):not(.activated)').length > 0
  ) {
    const { default: mermaid } = await import('mermaid');
    let idCount = $('.md-embed-mermaid.activating, .md-embed-mermaid.activated').length;
    const idMarker = 'mermaid_elem_';
    const instances = parentElement.find(
      '.md-embed-mermaid:not(.activating):not(.activated)'
    );
    instances.each(function embedMermaid() {
      const root = $(this);
      $(this).find('.embed-loading').addClass('loading');
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
      mermaid.render(elemId, definition, (svg) => {
        containerElem.html(svg);
        root.addClass('activated').removeClass('activating');
      });
    });
  }
}

export default addMermaidEmbed;
