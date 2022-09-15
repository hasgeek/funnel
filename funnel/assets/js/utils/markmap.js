import { Transformer } from 'markmap-lib';

const MarkmapEmbed = {
  addMarkmap() {
    const transformer = new Transformer();
    const { Markmap, loadCSS, loadJS } = window.markmap;

    $('.language-markmap').each(function embedMarkmap() {
      const { root, features } = transformer.transform($(this).find('code').text());
      const { styles, scripts } = transformer.getUsedAssets(features);
      if (styles) loadCSS(styles);
      if (scripts) loadJS(scripts, { getMarkmap: () => window.markmap });
      const random = Math.floor(Math.random() * 100);
      const markmapID = `#markmap-${random}`;
      const markmapSVG = `<svg id="markmap-${random}"></svg>`;
      $(this).parent().append(markmapSVG);
      const svgEl = document.querySelector(markmapID);
      const options = {};
      Markmap.create(svgEl, options, root);
    });
  },
  loadMarkmap() {
    const self = this;
    const CDN = [
      'https://cdn.jsdelivr.net/npm/d3@6',
      'https://cdn.jsdelivr.net/npm/markmap-view',
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
          loadMarkmapScript();
        } else {
          self.addMarkmap();
        }
      });
    };
    if (window.markmap !== 'function') {
      loadMarkmapScript();
    } else {
      self.addMarkmap();
    }
  },
  init() {
    if ($('.language-markmap').length > 0) {
      this.loadMarkmap();
    }
  },
};

export default MarkmapEmbed;
