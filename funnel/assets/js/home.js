$(() => {
  window.HasGeek.HomeInit = function() {
    // Adjust the height of schedule card to match spotlight card's height
    $(window).on('load', function() {
      if ($('.js-schedule-card')) {
        $('.js-schedule-card').height($('.spotlight__card').height());
      }
    });

    // Expand CFP section
    $('.jquery-show-all').click(function showAll(event) {
      event.preventDefault();
      const projectElemClass = `.${$(this).data('projects')}`;
      $(projectElemClass).removeClass('mui--hide');
      $(this).addClass('mui--hide');
    });

    // Truncate CFP cards tagline text
    $('.cfp-truncate').succinct({
      size: 125,
    });
  };
});
