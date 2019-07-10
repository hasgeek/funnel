import { Utils, ScrollActiveMenu, LazyloadImg } from './util';

$(() => {
  window.HasGeek = {};

  Utils.collapse();
  Utils.smoothScroll();
  Utils.scrollTabs();
  Utils.navSearchForm();

  let intersectionObserverComponents = function() {
    ScrollActiveMenu.init('page-navbar', 'sub-navbar__item', 'sub-navbar__item--active');
    LazyloadImg.init('js-lazyload-img');
  };

  if(document.querySelector('#page-navbar') || document.querySelector('.js-lazyload-img') ||
    document.querySelector('.js-lazyload-results')) {
    if (!('IntersectionObserver' in global &&
    'IntersectionObserverEntry' in global &&
    'intersectionRatio' in IntersectionObserverEntry.prototype)) {
      let polyfill = document.createElement('script');
      polyfill.setAttribute('type','text/javascript');
      polyfill.setAttribute('src','https://cdn.polyfill.io/v2/polyfill.min.js?features=IntersectionObserver');
      polyfill.onload = function() {
        intersectionObserverComponents();
      };
      document.head.appendChild(polyfill);
    }
    else {
      intersectionObserverComponents();
    }
  }

  if(!'URLSearchParams' in window) {
    let polyfill = document.createElement('script');
    polyfill.setAttribute('type','text/javascript');
    polyfill.setAttribute('src','https://cdnjs.cloudflare.com/ajax/libs/url-search-params/1.1.0/url-search-params.js');
    document.head.appendChild(polyfill);
  }

  // Send click events to Google analytics
  $('.mui-btn, a').click(function gaHandler() {
    let action = $(this).attr('data-action') || $(this).attr('title') || $(this).html();
    let target = $(this).attr('href') || '';
    Utils.sendToGA('click', action, target);
  });

  $('.jquery-show-all').click(function showAll(event) {
    event.preventDefault();
    let projectElemClass = `.${$(this).data('projects')}`;
    $(projectElemClass).removeClass('mui--hide');
    $(this).addClass('mui--hide');
  });

});
