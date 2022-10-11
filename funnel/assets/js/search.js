import 'htmx.org';
import Utils from './utils/helper';
import LazyloadImg from './utils/lazyloadimage';

const Search = {
  updateMetaTags(searchType, url = '') {
    const q = Utils.getQueryString('q');
    const type = Utils.getQueryString('type');
    const count = this.count[type];
    const title = window.gettext('Search results: %s', q);
    const description = window.gettext('%u results found for %s', count, q);

    $('title').html(title);
    $('meta[name=DC\\.title]').attr('content', title);
    $('meta[property=og\\:title]').attr('content', title);
    $('meta[name=description]').attr('content', description);
    $('meta[property=og\\:description]').attr('content', description);
    if (url) {
      $('link[rel=canonical]').attr('href', url);
      $('meta[property=og\\:url]').attr('content', url);
    }
  },
  afterFetch(activeTab = '') {
    if ($(activeTab).is(this.config.tabElem)) {
      $(this.config.tabElem).removeClass(this.config.activetabClassName);
      $(activeTab).addClass(this.config.activetabClassName);
      $(this.config.tabWrapperElem).animate(
        {
          scrollLeft: document.querySelector(`.${this.config.activetabClassName}`)
            .offsetLeft,
        },
        'slow'
      );
    }
    Utils.truncate();
    LazyloadImg.init('js-lazyload-img');
    if ($(activeTab).is(this.config.tabElem)) {
      this.updateMetaTags();
    }
  },
  init(config) {
    this.config = config;
    const countHash = {};
    config.counts.forEach((count) => {
      countHash[count.type] = count.count;
    });
    this.count = countHash;
    document.body.addEventListener('htmx:afterOnLoad', (event) => {
      this.afterFetch(event.detail.elt);
    });
  },
};

$(() => {
  window.Hasgeek.searchInit = function searchInit(config) {
    Search.init(config);
  };
});
