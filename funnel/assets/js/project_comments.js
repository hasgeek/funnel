import { Comments } from './util';

$(() => {
  window.HasGeek.ProjectCommentsInit = function(pageUrl) {
    Comments.init(pageUrl);
  };
});
