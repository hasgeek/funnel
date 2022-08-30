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
  addTypeformEmbed(typeformId, parentElem, loadScript) {
    if (!$(parentElem).find(`#typeform-${typeformId}`).length) {
      const typeformDiv = `<div class="typeform-wrapper" id="typeform-${typeformId}" data-tf-widget="${typeformId}" data-tf-inline-on-mobile data-tf-medium="snippet" ></div>`;
      parentElem.append(typeformDiv);
      if (!loadScript) window.tf.load();
    }
  },
  init(containerDiv) {
    const self = this;
    $(containerDiv)
      .find('a')
      .each(function isTypeformUrl() {
        const txt = $(this).attr('href');
        let urlSplit;
        let typeformId;
        let parentDiv;
        let loadScript;
        if (txt.includes('typeform.com')) {
          loadScript = self.loadTypeFormEmbed();
          urlSplit = txt.split('/');
          typeformId = urlSplit.pop();
          typeformId = typeformId.includes('?') ? typeformId.split('?')[0] : typeformId;
          parentDiv = $(this).parents(containerDiv);
          $(this).remove();
          if (typeformId) {
            self.addTypeformEmbed(typeformId, parentDiv, loadScript);
          }
        }
      });
  },
};

export default TypeformEmbed;
