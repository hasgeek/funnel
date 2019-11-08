export const Proposal = {
  init() {
    $('button[name="transition"][value="delete"]').click(function(e) {
      if (!window.confirm('Do you really want to delete this proposal?')) {
        e.preventDefault();
      }
    });
  },
};

export const Comments = {
  init(pageURL) {
    $('.comment .js-collapse').click(function() {
      $(this).addClass('mui--hide');
      $(this)
        .siblings('.js-uncollapse')
        .removeClass('mui--hide');
      $(this)
        .parent()
        .siblings('.comment--body')
        .slideUp('fast');
      $(this)
        .parent()
        .siblings('.comment--children')
        .slideUp('fast');
      return false;
    });

    $('.comment .js-uncollapse').click(function() {
      $(this).addClass('mui--hide');
      $(this)
        .siblings('.js-collapse')
        .removeClass('mui--hide');
      $(this)
        .parent()
        .siblings('.comment--body')
        .slideDown('fast');
      $(this)
        .parent()
        .siblings('.comment--children')
        .slideDown('fast');
      return false;
    });

    $('.comment .js-comment-reply').click(function() {
      const cfooter = $(this).parent();
      $('#comment-form input[name="parent_id"]').val(cfooter.attr('data-id'));
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $('#toplevel-comment').removeClass('mui--hide');
      $('#comment-submit').val('Reply'); // i18n gotcha
      cfooter.after($('#comment-form'));
      $('#comment-form textarea').focus();
      return false;
    });

    $('#toplevel-comment a').click(function() {
      $('#comment-form  input[name="parent_id"]').val('');
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $('#comment-submit').val('Post comment'); // i18n gotcha
      $(this)
        .parent()
        .after($('#comment-form'));
      $(this)
        .parent()
        .addClass('mui--hide');
      $('#comment-form textarea').focus();
      return false;
    });

    $('.comment .js-comment-delete').click(function() {
      const cfooter = $(this).parent();
      $('#delcomment input[name="comment_id"]').val(cfooter.attr('data-id'));
      $('#delcomment').attr('action', cfooter.attr('data-delete-url'));
      $('#delcomment')
        .removeClass('mui--hide')
        .hide()
        .insertAfter(cfooter)
        .slideDown('fast');
      return false;
    });

    $('#comment-delete-cancel').click(() => {
      $('#delcomment').slideUp('fast');
      return false;
    });

    $('.comment .js-comment-edit').click(function() {
      const cfooter = $(this).parent();
      const cid = cfooter.attr('data-id');
      $('#comment-form textarea').val('Loading...'); // i18n gotcha
      $.getJSON(`${pageURL}/comments/${cid}/json`, data => {
        $('#comment-form textarea').val(data.message);
      });
      $('#comment-form input[name="parent_id"]').val('');
      $('#comment-form input[name="comment_edit_id"]').val(cid);
      $('#toplevel-comment').removeClass('mui--hide');
      $('#comment-submit').val('Save changes'); // i18n gotcha
      cfooter.after($('#comment-form'));
      $('#comment-form textarea').focus();
      return false;
    });
  },
};

export const Video = {
  /* Takes argument
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (extractYoutubeId).
    The videoID is then used to generate the iframe html.
    The generated iframe is added to the video container element.
  */
  getVideoTypeAndId(url) {
    const regexMatch = url.match(
      /(http:|https:|)\/\/(player.|www.)?(vimeo\.com|youtu(be\.com|\.be|be\.googleapis\.com))\/(video\/|embed\/|watch\?v=|v\/)?([A-Za-z0-9._%-]*)(&\S+)?/
    );
    let type = '';
    if (regexMatch[3].indexOf('youtu') > -1) {
      type = 'youtube';
    } else if (regexMatch[3].indexOf('vimeo') > -1) {
      type = 'vimeo';
    }
    return {
      type,
      videoId: regexMatch[6],
    };
  },
  embedIframe(videoWrapper, videoUrl) {
    let videoEmbedUrl;
    const { type, videoId } = this.getVideoTypeAndId(videoUrl);
    if (type === 'youtube') {
      videoEmbedUrl = `<iframe src='//www.youtube.com/embed/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    } else if (type === 'vimeo') {
      videoEmbedUrl = `<iframe src='https://player.vimeo.com/video/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    }
    videoWrapper.innerHTML = videoEmbedUrl;
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
    return labelTxt.trim().replace(/\*$/, '');
  },
  updateLabels(label = '', attr = '', action = true) {
    if (action) {
      if (label !== attr) {
        $(`.label[data-labeltxt="${attr}"]`).remove();
      }
      const span = `<span class="label mui--text-caption mui--text-bold" data-labeltxt="${attr}">${label}</span>`;
      $('#label-select').append(span);
    } else {
      $(`.label[data-labeltxt="${attr}"]`).remove();
    }
  },
};

$(() => {
  window.HasGeek.ProposalInit = function({
    pageUrl,
    videoWrapper = '',
    videoUrl = '',
  }) {
    Proposal.init();
    Comments.init(pageUrl);
    LabelsWidget.init();

    if (videoWrapper) {
      Video.embedIframe(videoWrapper, videoUrl);
    }
  };
});
