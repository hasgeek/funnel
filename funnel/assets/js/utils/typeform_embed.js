const TypeformEmbed = {
  loadTypeFormEmbed() {
    if (!window.tf) {
      const head = document.querySelector('head');
      const typeformStyle = document.createElement('link');
      typeformStyle.rel = 'stylesheet';
      typeformStyle.href = 'https://embed.typeform.com/next/css/popup.css';
      head.appendChild(typeformStyle);

      const body = document.querySelector('body');
      const typeformScript = document.createElement('script');
      typeformScript.type = 'text/javascript';
      typeformScript.src = 'https://embed.typeform.com/next/embed.js';
      body.appendChild(typeformScript);
      return true;
    }
    return false;
  },
  addTypeformEmbed(typeformId, anchorTag, parentDiv, loadScript) {
    if (!$(parentDiv).find(`#typeform-${typeformId}`).length) {
      const typeformDiv = `<div class="typeform-wrapper" id="typeform-${typeformId}" data-tf-widget="${typeformId}" data-tf-inline-on-mobile data-tf-medium="snippet" ></div>`;
      $(anchorTag).after(typeformDiv);
      $(anchorTag).remove();
      if (!loadScript) window.tf.load();
    }
  },
  init(containerDiv) {
    const self = this;
    $(containerDiv)
      .find('a')
      .each(function isTypeformUrl() {
        const anchorTag = this;
        const txt = $(anchorTag).attr('href');
        let urlSplit;
        let typeformId;
        let parentDiv;
        let loadScript;
        if (txt.includes('typeform.com')) {
          loadScript = self.loadTypeFormEmbed();
          urlSplit = txt.split('/');
          typeformId = urlSplit.pop();
          typeformId = typeformId.includes('?') ? typeformId.split('?')[0] : typeformId;
          parentDiv = $(anchorTag).parents(containerDiv);
          if (typeformId) {
            self.addTypeformEmbed(typeformId, anchorTag, parentDiv, loadScript);
          }
        }
      });
  },
};

export default TypeformEmbed;
