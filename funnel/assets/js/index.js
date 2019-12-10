$(() => {
  window.HasGeek.HomeInit = function(config) {
    // Adjust the height of schedule card to match spotlight card's height
    $(window).on('load', function() {
      if ($('.js-schedule-card')) {
        $('.js-schedule-card').height($('.card--spotlight').height());
      }
    });

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

    $('.js-truncate-title').trunk8({
      lines: 2,
    });

    $('.js-truncate-tagline').trunk8({
      lines: 3,
      fill:
        '&hellip;<span class="js-read-more-text mui--text-hyperlink read-more">read more</span>',
    });

    $('.js-read-more-text').click(function() {
      $('.js-truncate-tagline').trunk8('revert');
    });
  };
});
