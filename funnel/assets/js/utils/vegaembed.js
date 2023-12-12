async function addVegaSupport(container) {
  const parentElement = $(container || 'body');
  if (
    parentElement.find('.md-embed-vega-lite:not(.activating, .activated)').length > 0
  ) {
    const { default: embed } = await import('vega-embed');
    const options = {
      renderer: 'svg',
      actions: {
        source: false,
        editor: false,
        compiled: false,
      },
    };

    parentElement
      .find('.md-embed-vega-lite:not(.activating):not(.activated)')
      .each(async function embedVegaChart() {
        const root = $(this);
        root.find('.embed-loading').addClass('loading');
        root.addClass('activating');
        const embedded = await embed(
          root.find('.embed-container')[0],
          JSON.parse(root.find('.embed-content').text()),
          options
        );
        embedded.view.runAfter(() => {
          root.addClass('activated').removeClass('activating');
        });
      });
  }
}

export default addVegaSupport;
