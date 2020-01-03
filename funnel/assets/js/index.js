import { SaveProject } from './util';

$(() => {
  window.HasGeek.HomeInit = function(config) {
    function getRandomNumber() {
      return Math.floor(
        Math.random() * Math.floor(config.hgBannerImgList.length)
      );
    }
    function getImagePath(num) {
      return config.ImgFolderPath + config.hgBannerImgList[num];
    }

    // Random display of HasGeek banner
    if (config.hgBannerImgList && config.hgBannerImgList.length) {
      let randomNumList = [];
      do {
        let randomNum = getRandomNumber();
        if (randomNum > 0 && randomNumList.indexOf(randomNum) === -1) {
          randomNumList.push(randomNum);
        }
      } while (randomNumList.length < 4);
      $('.js-hg-banner').each(function(index) {
        $(this).attr('src', getImagePath(randomNumList[index]));
      });
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
