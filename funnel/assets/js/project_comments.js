import { Comments } from './util';

$(() => {
  window.Hasgeek.ProjectCommentsInit = function (pageUrl) {
    Comments.init(pageUrl);
  };
});
