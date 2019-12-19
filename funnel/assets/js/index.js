import { SaveProject } from './util';

$(() => {
  window.HasGeek.HomeInit = function(config) {
    // Random display of HasGeek banner
    if (config.hgBannerImgList && config.hgBannerImgList.length) {
      let random = Math.floor(
        Math.random() * Math.floor(config.hgBannerImgList.length)
      );
      let bannerFile = config.ImgFolderPath + config.hgBannerImgList[random];
      $('.js-hg-banner').attr('src', bannerFile);
    } else {
      $('.js-hg-banner').attr('src', config.defaultBanner);
    }

    // Expand CFP section
    $('.jquery-show-all').click(function showAll(event) {
      event.preventDefault();
      const projectElemClass = `.${$(this).data('projects')}`;
      $(projectElemClass).removeClass('mui--hide');
      $(this).addClass('mui--hide');
    });

    $('.js-save-form').each(function() {
      let projectSaveConfig = {
        formId: $(this).attr('id'),
        postUrl: $(this).attr('action'),
      };
      SaveProject(projectSaveConfig);
    });
  };
});
