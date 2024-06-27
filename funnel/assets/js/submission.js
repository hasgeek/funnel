import toastr from 'toastr';
import Form from './utils/formhelper';
import { Widgets } from './utils/form_widgets';
import WebShare from './utils/webshare';
import initEmbed from './utils/initembed';

export const Submission = {
  init(toggleId) {
    if (toggleId) Widgets.activateToggleSwitch(toggleId);
    WebShare.enableWebShare();
    $('.js-subscribe-btn').on('click', function subscribeComments(event) {
      event.preventDefault();
      const form = $(this).parents('form')[0];
      const url = $(form).attr('action');
      Submission.postSubscription(url, form);
    });
  },
  async postSubscription(url, form) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(new FormData(form)).toString(),
    }).catch(() => {
      toastr.error(window.Hasgeek.Config.errorMsg.networkError);
    });
    if (response && response.ok) {
      const responseData = await response.json();
      if (responseData) {
        if (responseData.message) {
          toastr.success(responseData.message);
        }
        $('.js-subscribed, .js-unsubscribed').toggleClass('mui--hide');
      }
    } else {
      Form.getFetchError(response);
    }
  },
};

export const LabelsWidget = {
  init() {
    const self = this;

    // On load, if the radio has been selected, then check mark the listwidget label
    $('.listwidget input[type="radio"]').each(function loadCheckMarkToLabel() {
      if (this.checked) {
        $(this).parent().parent().prev('.mui-form__label').addClass('checked');
      }
    });

    $('.listwidget .mui-form__label').on('click', function uncheckLabel() {
      if ($(this).hasClass('checked')) {
        $(this).removeClass('checked');
        $(this).siblings().find('input[type="radio"]').prop('checked', false);
        const attr = self.getLabelTxt($(this).text().trim());
        self.updateLabels('', attr, false);
      } else {
        $(this).addClass('checked');
        $(this).siblings().find('input[type="radio"]').first().trigger('click');
      }
    });

    // Add check mark to listwidget label
    $('.listwidget input[type="radio"]').on('change', function addCheckMarkToLabel() {
      const label = $(this).parent().parent().prev('.mui-form__label');
      label.addClass('checked');
      const labelTxt = `${self.getLabelTxt(label.text())}: ${self.getLabelTxt(
        $(this).parent().find('label').text(),
      )}`;
      const attr = self.getLabelTxt(label.text());
      self.updateLabels(labelTxt, attr, this.checked);
    });

    $('.mui-checkbox input[type="checkbox"]').on(
      'change',
      function clickLabelCheckbox() {
        const labelTxt = self.getLabelTxt($(this).parent('label').text());
        self.updateLabels(labelTxt, labelTxt, this.checked);
      },
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
        '<span class="label mui--text-caption mui--text-bold"></span>',
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
  window.Hasgeek.SubmissionInit = function init(markdownId, toggleId = '') {
    Submission.init(toggleId);
    window.Hasgeek.LabelsWidget = LabelsWidget.init.bind(LabelsWidget);
    initEmbed(markdownId);
  };
});
