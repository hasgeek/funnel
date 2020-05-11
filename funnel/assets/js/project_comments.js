import { Utils, Comments } from './util';

$(() => {
  window.HasGeek.ProjectCommentsInit = function (pageUrl, sectionId) {
    Utils.animateScrollTo($(sectionId).offset().top);
    Comments.init(pageUrl);
  };
});
