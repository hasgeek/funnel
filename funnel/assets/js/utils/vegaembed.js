/* global vegaEmbed */

function addVegaChart() {
  $('.md-embed-vega-lite:not(.activated)').each(async function embedVegaChart() {
    const root = $(this);
    const embedded = await vegaEmbed(
      this,
      JSON.parse($(this).find('.embed-content').text()),
      {
        renderer: 'svg',
        actions: {
          source: false,
          editor: false,
          compiled: false,
        },
      }
    );
    embedded.view.runAfter(() => {
      root.addClass('activated');
    });
  });
}

function addVegaSupport() {
  if ($('.md-embed-vega-lite:not(.activated)').length > 0) {
    const vegaliteCDN = [
      'https://cdn.jsdelivr.net/npm/vega@5',
      'https://cdn.jsdelivr.net/npm/vega-lite@5',
      'https://cdn.jsdelivr.net/npm/vega-embed@6',
    ];
    if (typeof printMessage !== 'function') {
      let vegaliteUrl = 0;
      const loadVegaScript = () => {
        $.ajax({
          url: vegaliteCDN[vegaliteUrl],
          dataType: 'script',
          cache: true,
        }).done(() => {
          if (vegaliteUrl < vegaliteCDN.length) {
            vegaliteUrl += 1;
            loadVegaScript();
          }
          // Once all vega js is loaded, initialize vega visualization on all pre tags with class 'md-embed-vega-lite'
          if (vegaliteUrl === vegaliteCDN.length) {
            addVegaChart();
          }
        });
      };
      loadVegaScript();
    } else {
      addVegaChart();
    }
  }
}

export default addVegaSupport;
