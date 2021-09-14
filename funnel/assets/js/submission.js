import Form from './utils/formhelper';

export const Submission = {
  init() {
    $('.js-subscribe-btn').on('click', function subscribeComments(event) {
      event.preventDefault();
      const form = $(this).parents('form');
      const formData = $(form).serializeArray();
      $.ajax({
        type: 'POST',
        url: $(form).attr('action'),
        data: formData,
        dataType: 'json',
        timeout: window.Hasgeek.Config.ajaxTimeout,
        success(responseData) {
          if (responseData && responseData.message) {
            window.toastr.success(responseData.message);
          }
          $('.js-subscribed, .js-unsubscribed').toggleClass('mui--hide');
          Form.updateFormNonce(responseData);
        },
        error(response) {
          Form.handleAjaxError(response);
        },
      });
    });
  },
};

export const LabelsWidget = {
  init() {
    const Widget = this;

    // On load, if the radio has been selected, then check mark the listwidget label
    $('.listwidget input[type="radio"]').each(function loadCheckMarkToLabel() {
      if (this.checked) {
        $(this).parent().parent().prev('.mui-form__label').addClass('checked');
      }
    });

    $('.listwidget .mui-form__label').click(function uncheckLabel() {
      if ($(this).hasClass('checked')) {
        $(this).removeClass('checked');
        $(this).siblings().find('input[type="radio"]').prop('checked', false);
        const attr = Widget.getLabelTxt($(this).text().trim());
        Widget.updateLabels('', attr, false);
      } else {
        $(this).addClass('checked');
        $(this).siblings().find('input[type="radio"]').first().click();
      }
    });

    // Add check mark to listwidget label
    $('.listwidget input[type="radio"]').change(function addCheckMarkToLabel() {
      const label = $(this).parent().parent().prev('.mui-form__label');
      label.addClass('checked');
      const labelTxt = `${Widget.getLabelTxt(
        label.text()
      )}: ${Widget.getLabelTxt($(this).parent().find('label').text())}`;
      const attr = Widget.getLabelTxt(label.text());
      Widget.updateLabels(labelTxt, attr, this.checked);
    });

    $('.mui-checkbox input[type="checkbox"]').change(
      function clickLabelCheckbox() {
        const labelTxt = Widget.getLabelTxt($(this).parent('label').text());
        Widget.updateLabels(labelTxt, labelTxt, this.checked);
      }
    );

    // Open and close dropdown
    $('#label-select').on('click', () => {
      if ($('#label-dropdown fieldset').hasClass('active')) {
        $('#label-dropdown fieldset').removeClass('active');
      } else {
        $('#label-dropdown fieldset').addClass('active');
      }
    });

    $(document).on('click', (event) => {
      if (
        $('#label-select')[0] !== event.target &&
        !$(event.target).parents('#label-select').length &&
        !$(event.target).parents('#label-dropdown').length
      ) {
        $('#label-dropdown fieldset').removeClass('active');
      }
    });
  },
  getLabelTxt(labelTxt) {
    return labelTxt
      .trim()
      .replace(/\*$/, '')
      .replace(/script/g, '');
  },
  updateLabels(label = '', attr = '', action = true) {
    if (action) {
      if (label !== attr) {
        $(`.label[data-labeltxt='${attr}']`).remove();
      }
      const labelSpan = $(
        '<span class="label mui--text-caption mui--text-bold"></span>'
      )
        .attr('data-labeltxt', attr)
        .text(label);
      $('#label-select').append(labelSpan);
    } else {
      $(`.label[data-labeltxt='${attr}']`).remove();
    }
  },
};

$(() => {
  window.Hasgeek.SubmissionInit = Submission.init.bind(Submission);
  window.Hasgeek.LabelsWidget = LabelsWidget.init.bind(LabelsWidget);
});
