import { Comments } from './util';

$(() => {
  window.HasGeek.DisussionsInit = function (pageUrl) {
    Comments.init(pageUrl);
  };
});
