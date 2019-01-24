import { Utils, ScrollActiveMenu } from './util';

$(() => {
  window.HasGeek = {};

  Utils.collapse();
  Utils.smoothScroll();


  if(document.querySelector('#page-navbar')) {
    ScrollActiveMenu.init('page-navbar', 'sub-navbar__item', 'sub-navbar__item--active');
  }

  // Send click events to Google analytics
  $('.mui-btn, a').click(() => {
    var action = $(this).attr('data-action') || $(this).attr('title') || $(this).html();
    var target = $(this).attr('href') || '';
    Utils.sendToGA('click', action, target);
  });
});
