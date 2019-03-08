import { Utils, ScrollActiveMenu, LazyloadImg } from './util';

$(() => {
  window.HasGeek = {};

  Utils.collapse();
  Utils.smoothScroll();

  let intersectionObserverComponents = function() {
    ScrollActiveMenu.init('page-navbar', 'sub-navbar__item', 'sub-navbar__item--active');
    LazyloadImg.init('js-lazyload-img');
  };

  if(document.querySelector('#page-navbar') || document.querySelector('.js-lazyload-img')) {
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

  // Send click events to Google analytics
  $('.mui-btn, a').click(function gaHandler() {
    var action = $(this).attr('data-action') || $(this).attr('title') || $(this).html();
    var target = $(this).attr('href') || '';
    Utils.sendToGA('click', action, target);
  });

  $('.js-show-cfp-projects').click(function showAll(event) {
    event.preventDefault();
    $('.js-cfp-projects').removeClass('mui--hide');
    $(this).addClass('mui--hide');
  });
});
