export const Comments = {
  init(pageURL) {
    $('.comment .js-collapse').click(function() {
      $(this).addClass('mui--hide');
      $(this).siblings('.js-uncollapse').removeClass('mui--hide');
      $(this).parent().siblings('.comment--body').slideUp("fast");
      $(this).parent().siblings('.comment--children').slideUp("fast");
      return false;
    });

    $('.comment .js-uncollapse').click(function() {
      $(this).addClass('mui--hide');
      $(this).siblings('.js-collapse').removeClass('mui--hide');
      $(this).parent().siblings('.comment--body').slideDown("fast");
      $(this).parent().siblings('.comment--children').slideDown("fast");
      return false;
    });

    $('.comment .js-comment-reply').click(function() {
      var cfooter = $(this).parent();
      $('#comment-form input[name="parent_id"]').val(cfooter.attr('data-id'));
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $("#toplevel-comment").removeClass('mui--hide');
      $("#comment-submit").val("Reply"); // i18n gotcha
      cfooter.after($("#comment-form"));
      $("#comment-form textarea").focus();
      return false;
    });

    $('#toplevel-comment a').click(function() {
      $('#comment-form  input[name="parent_id"]').val('');
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $('#comment-submit').val("Post comment"); // i18n gotcha
      $(this).parent().after($('#comment-form'));
      $(this).parent().addClass('mui--hide');
      $('#comment-form textarea').focus();
      return false;
    });

    $('.comment .js-comment-delete').click(function() {
      var cfooter = $(this).parent();
      $('#delcomment input[name="comment_id"]').val(cfooter.attr('data-id'));
      $('#delcomment').attr('action', cfooter.attr('data-delete-url'))
      $('#delcomment').removeClass('mui--hide').hide().insertAfter(cfooter).slideDown("fast");
      return false;
    });

    $('#comment-delete-cancel').click(function() {
      $('#delcomment').slideUp('fast');
      return false;
    });

    $('.comment .js-comment-edit').click(function() {
      var cfooter = $(this).parent();
      var cid = cfooter.attr('data-id');
      $("#comment-form textarea").val("Loading..."); // i18n gotcha
      $.getJSON(pageURL+'/comments/'+cid+'/json', function(data) {
        $("#comment-form textarea").val(data.message);
      });
      $('#comment-form input[name="parent_id"]').val('');
      $('#comment-form input[name="comment_edit_id"]').val(cid);
      $('#toplevel-comment').removeClass('mui--hide');
      $('#comment-submit').val("Save changes"); // i18n gotcha
      cfooter.after($('#comment-form'));
      $('#comment-form textarea').focus();
      return false;
    });
  }
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
    let regexMatch = url.match(/(http:|https:|)\/\/(player.|www.)?(vimeo\.com|youtu(be\.com|\.be|be\.googleapis\.com))\/(video\/|embed\/|watch\?v=|v\/)?([A-Za-z0-9._%-]*)(&\S+)?/);
    let type = '';
    if (regexMatch[3].indexOf('youtu') > -1) {
      type = 'youtube';
    } else if (regexMatch[3].indexOf('vimeo') > -1) {
      type = 'vimeo';
    }
    return {
      type: type,
      videoId: regexMatch[6]
    };
  },
  embedIframe(videoWrapper, videoUrl) {
    let videoEmbedUrl;
    let {type, videoId} = this.getVideoTypeAndId(videoUrl);
    if(type === 'youtube') {
      videoEmbedUrl = `<iframe src='//www.youtube.com/embed/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    } else if(type === 'vimeo') {
      videoEmbedUrl = `<iframe src='https://player.vimeo.com/video/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    }
    videoWrapper.innerHTML = videoEmbedUrl;
  },
};

export const LabelsWidget = {
  init(config) {
    let Widget = this;
    Widget.config = config;

    // Open and close dropdown
    $('#label-select').on('click', function() {
      if(Widget.config.dropdown.hasClass('active')) {
        Widget.assignLabel();
      } else {
        Widget.getLabelForm();
      }
    });

    // Close dropdown on clicking outside dropdown wrapper
    $(document).on('click', function(event) {
      if ($('#label-select')[0] !== event.target && !$(event.target).parents('#label-select').length && !$(event.target).parents('#label-dropdown').length) {
        if(Widget.config.dropdown.hasClass('active')) {
          Widget.assignLabel();
        }
      }
    });
  },
  widgetInit() {
    let Widget = this;
    // On load, if the radio has been selected, then check mark the listwidget label
    $('.listwidget input[type="radio"]').each(function() {
      if(this.checked) {
        $(this).parent().parent().prev('.mui-form__label').addClass('checked');
      }
    });

    $('.listwidget .mui-form__label').click(function() {
      if($(this).hasClass('checked')) {
        $(this).removeClass('checked');
        let attr = Widget.getLabelTxt($(this).text().trim());
        let label = $(this).siblings().find('input[type="radio"]');
        let labelName = $(`input[name="${label.attr('name')}"]:checked`).val();
        label.prop('checked', false);
        Widget.updateLabels('', attr, labelName, false);
      } else {
        $(this).addClass('checked');
        $(this).siblings().find('input[type="radio"]').first().click();
      }
    });

    // Add check mark to listwidget label
    $('.listwidget input[type="radio"]').change(function() {
      let label = $(this).parent().parent().prev('.mui-form__label');
      label.addClass('checked');
      let labelTxt = `${Widget.getLabelTxt(label.text())}: ${Widget.getLabelTxt($(this).parent().find('label').text())}`;
      let attr = Widget.getLabelTxt(label.text());
      Widget.updateLabels(labelTxt, attr, $(this).val(), this.checked);
    });

    $('.add-label-form input[type="checkbox"]').change(function() {
      let labelTxt = Widget.getLabelTxt($(this).parent('label').text());
      Widget.updateLabels(labelTxt, labelTxt, $(this).attr('name'), this.checked);
    });

    Widget.config.addList = Widget.config.labels.slice(); 
    Widget.config.removeList = [];
  },
  getLabelForm() {
    let Widget = this;
    $.ajax({
      type: 'GET',
      url: Widget.config.getFormUrl,
      dataType: 'json',
      timeout: 15000,
      success: function (response) {
        Widget.config.dropdown.html(response.admin_form);
        Widget.widgetInit();
        Widget.config.dropdown.addClass('active');
      },
      error: function (response) {
        let errorMsg = '';
        if (response.readyState === 4) {
          if (response.status === 500) {
            errorMsg ='Internal Server Error. Please reload and try again.';
          } else {
            errorMsg = JSON.parse(response.responseText).error_description;
          }
        } else {
          errorMsg = 'Unable to connect. Please reload and try again.';
        }
        window.toastr.error(errorMsg);
      },
    });
  },
  getLabelTxt(labelTxt) {
    return labelTxt.trim().replace(/\*$/, '');
  },
  updateLabels(label='', attr='', name='', action=true) {
    if(action) {
      if(label !== attr) {
        let labelName = $(`.label[data-labeltxt="${attr}"]`).data('labelname');
        $(`.label[data-labeltxt="${attr}"]`).remove();
        this.removeLabel(labelName);
      }
      let span = `<span class="label mui--text-caption mui--text-bold" data-labeltxt="${attr}" data-labelname="${name}">${label}</span>`;
      this.config.select.append(span);
      this.addLabel(name);
    } else {
      $(`.label[data-labelname="${name}"]`).remove();
      this.removeLabel(name);
    }
  },
  removeLabel(name='') {
    if(this.config.labels.indexOf(name) > -1 ) {
      this.config.removeList.push(name);
    }
    if (this.config.addList.indexOf(name) > -1) {
      this.config.addList.splice(this.config.addList.indexOf(name), 1);
    }
  },
  addLabel(name='') {
    if (this.config.addList.indexOf(name) === -1) {
      this.config.addList.push(name)
    }
    if (this.config.removeList.indexOf(name) > -1) {
      this.config.removeList.splice(this.config.removeList.indexOf(name), 1);
    }
  },
  assignLabel() {
    let Widget = this;
    Widget.config.dropdown.removeClass('active');
    Widget.config.dropdown.html('');

    $.ajax({
      type: 'POST',
      url: Widget.config.submitUrl,
      dataType: 'json',
      contentType: 'application/json',
      data: JSON.stringify({
        addLabel: Widget.config.addList,
        removeLabel: Widget.config.removeList
      }),
      timeout: 15000,
      success: function (response) {
        Widget.config.labels = response.labels ;
      },
      error: function (response) {
        let errorMsg = '';
        if (response.readyState === 4) {
          if (response.status === 500) {
            errorMsg ='Internal Server Error. Please reload and try again.';
          } else {
            errorMsg = JSON.parse(response.responseText).error_description;
          }
        } else {
          errorMsg = 'Unable to connect. Please reload and try again.';
        }
        window.toastr.error(errorMsg);
      },
    });
  },
};

$(() => {
  window. HasGeek.ProposalInit = function ({pageUrl, videoWrapper= '', videoUrl= '', labelWidget=''}) {
    Comments.init(pageUrl);
    LabelsWidget.init(labelWidget);

    if (videoWrapper) {
      Video.embedIframe(videoWrapper, videoUrl);
    }
  };
});
