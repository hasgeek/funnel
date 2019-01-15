import { Utils } from './util';

$(() => {
  window.HasGeek = {};

  Utils.collapse();
  Utils.smoothScroll();

  // Send click events to Google analytics
  $('a').click(function clickHandler() {
    let target = $(this).attr('href');
    let action = $(this).attr('title') || $(this).html();
    Utils.sendToGA('click', action, target);
  });
});
