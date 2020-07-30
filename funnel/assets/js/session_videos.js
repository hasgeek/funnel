$(() => {
  window.Hasgeek.SessionVideoInit = function () {
    $('.js-video-duration').each(function () {
      let durationInSeconds = $(this).data('duration');
      let date = new Date(null);
      date.setSeconds(durationInSeconds);
      let duration = date.toISOString().substr(11, 8);
      $(this).html(duration);
    });
  };
});
