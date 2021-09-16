$(() => {
  // Set current date & time in cfp_start_at input field and show cfp_end_at input field.
  $('button[name="open-now"]').click((event) => {
    event.preventDefault();
    const now = new Date(
      new Date().getTime() + new Date().getTimezoneOffset() * -60 * 1000
    );
    $('#cfp_start_at').val(now.toISOString().slice(0, 16));
    $('.js-cfp-start-at, .js-cfp-end-at').removeClass('mui--hide');
  });

  // Show cfp_start_at and cfp_end_at input field.
  $('button[name="later"]').click((event) => {
    event.preventDefault();
    $('.js-cfp-start-at, .js-cfp-end-at').removeClass('mui--hide');
  });
});
