$(() => {
  window.HasGeek.HomeInit = function() {
    // Adjust the height of schedule card to match spotlight card's height
    $(window).on('load', function() {
      if ($('.js-schedule-card')) {
        $('.js-schedule-card').height($('.card--spotlight').height());
      }
    });

    // Expand CFP section
    $('.jquery-show-all').click(function showAll(event) {
      event.preventDefault();
      const projectElemClass = `.${$(this).data('projects')}`;
      $(projectElemClass).removeClass('mui--hide');
      $(this).addClass('mui--hide');
    });
  };
});
