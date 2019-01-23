import { Utils, ScrollActiveMenu } from './util';

$(() => {
  window.HasGeek = {};

  Utils.collapse();
  Utils.smoothScroll();


  if(document.querySelector('.sub-navbar__item')) {
    ScrollActiveMenu.init('sub-navbar__item', 'sub-navbar__item--active');
  }

  // Send click events to Google analytics
  $('a').click(function clickHandler() {
    let target = $(this).attr('href');
    let action = $(this).attr('title') || $(this).html();
    Utils.sendToGA('click', action, target);
  });
});
