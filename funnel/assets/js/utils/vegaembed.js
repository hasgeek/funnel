/* global vegaEmbed */

function addVegaChart() {
  $('.language-vega-lite').each(function embedVegaChart() {
    vegaEmbed(this, JSON.parse($(this).find('code').text()), {
      renderer: 'svg',
      actions: {
        source: false,
        editor: false,
        compiled: false,
      },
    });
  });
}

function addVegaSupport() {
  if ($('.language-vega-lite').length > 0) {
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
          // Once all vega js is loaded, initialize vega visualization on all pre tags with class 'language-vega-lite'
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
