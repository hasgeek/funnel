import { Video, Comments } from './util';

export const Proposal = {
  init() {
    $('button[name="transition"][value="delete"]').click(function(e) {
      if (!window.confirm('Do you really want to delete this proposal?')) {
        e.preventDefault();
      }
    });
  },
};

export const LabelsWidget = {
  init() {
    const Widget = this;

    // On load, if the radio has been selected, then check mark the listwidget label
    $('.listwidget input[type="radio"]').each(function() {
      if (this.checked) {
        $(this)
          .parent()
          .parent()
          .prev('.mui-form__label')
          .addClass('checked');
      }
    });

    $('.listwidget .mui-form__label').click(function() {
      if ($(this).hasClass('checked')) {
        $(this).removeClass('checked');
        $(this)
          .siblings()
          .find('input[type="radio"]')
          .prop('checked', false);
        const attr = Widget.getLabelTxt(
          $(this)
            .text()
            .trim()
        );
        Widget.updateLabels('', attr, false);
      } else {
        $(this).addClass('checked');
        $(this)
          .siblings()
          .find('input[type="radio"]')
          .first()
          .click();
      }
    });

    // Add check mark to listwidget label
    $('.listwidget input[type="radio"]').change(function() {
      const label = $(this)
        .parent()
        .parent()
        .prev('.mui-form__label');
      label.addClass('checked');
      const labelTxt = `${Widget.getLabelTxt(
        label.text()
      )}: ${Widget.getLabelTxt(
        $(this)
          .parent()
          .find('label')
          .text()
      )}`;
      const attr = Widget.getLabelTxt(label.text());
      Widget.updateLabels(labelTxt, attr, this.checked);
    });

    $('.add-label-form input[type="checkbox"]').change(function() {
      const labelTxt = Widget.getLabelTxt(
        $(this)
          .parent('label')
          .text()
      );
      Widget.updateLabels(labelTxt, labelTxt, this.checked);
    });

    // Open and close dropdown
    $('#label-select').on('click', () => {
      if ($('#label-dropdown fieldset').hasClass('active')) {
        $('#label-dropdown fieldset').removeClass('active');
      } else {
        $('#label-dropdown fieldset').addClass('active');
      }
    });

    $(document).on('click', event => {
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
      let labelSpan = $(
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
  window.HasGeek.ProposalInit = function({ videoWrapper = '', videoUrl = '' }) {
    Proposal.init();
    Comments.init();
    LabelsWidget.init();

    if (videoWrapper) {
      Video.embedIframe(videoWrapper, videoUrl);
    }
  };
});
