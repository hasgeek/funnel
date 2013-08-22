function radioHighlight(radioName, highlightClass) {
    var selector = "input[name='" + radioName + "']";
    $(selector + ":checked").parent().addClass(highlightClass);
    var handler = function() {
        $(selector).parent().removeClass(highlightClass);
        $(selector + ":checked").parent().addClass(highlightClass);
    };
    $(selector).change(handler);
    $(selector).click(handler);
}

function markdownPreview() {
    converter = new Showdown.converter();
    $(".markdown-field .button").click(function(e) {
        var field = $(this).closest('.markdown-field').parent().find('textarea');
        var action = $(this).attr('id').split('-')[1];
        var field_id = $(field).attr('id');
        var preview_id = field_id + "-preview-block";
        var control = $(field).parent();
        var write = $("#"+field_id+"-write");
        var preview = $("#"+field_id+"-preview");
        if (action=="write") {
            if ($('#'+preview_id).length > 0) {
                $('#'+preview_id).hide();
                $('#'+preview_id).children().remove();
            }
            $(control).show();
            $(write).attr('class', 'button-selected');
            $(preview).attr('class', 'button');
        } else if (action=="preview") {
            var html_text;
            if ($(field).val() === "") {
                html_text = $('<p>').html("Nothing to preview");
            } else {
                html_text = $(converter.makeHtml($(field).val()));
            }
            $(preview).attr('class', 'button-selected');
            $(write).attr('class', 'button');
            if ($('#'+preview_id).length === 0) {
                var preview_control = $('<div>').attr('class', 'preview-control');
                preview = $('<div>').attr('id', preview_id).attr('class', 'preview-block');
                $(preview).append(html_text);
                $(preview_control).append(preview);
                $(control).parent().append(preview_control);
                $(control).hide();
            } else {
                $(control).hide();
                $('#'+preview_id).children().remove();
                $(html_text).appendTo($('#'+preview_id));
                $('#'+preview_id).show();
            }
        }
        e.preventDefault();
    });
}

function commentsInit(pageURL) {
    $(".comments .collapse").click(function() {
        $(this).addClass('hidden');
        $(this).parent().find('.uncollapse').removeClass('hidden');
        $(this).parent().parent().find('.com-body').slideUp("fast");
        $(this).parent().parent().parent().find('.com-children').slideUp("fast");
        return false;
    });

    $(".comments .uncollapse").click(function() {
        $(this).addClass('hidden');
        $(this).parent().find('.collapse').removeClass('hidden');
        $(this).parent().parent().find('.com-body').slideDown("fast");
        $(this).parent().parent().parent().find('.com-children').slideDown("fast");
        return false;
    });

    $(".comments .comment-reply").click(function() {
        var cfooter = $(this).parent();
        $('#newcomment input[name="parent_id"]').val(cfooter.attr('data-id'));
        $('#newcomment input[name="comment_edit_id"]').val('');
        $("#toplevel-comment").removeClass('hidden');
        $("#comment-submit").val("Reply"); // i18n gotcha
        cfooter.after($("#newcomment"));
        $("#newcomment textarea").focus();
        return false;
    });

    $("#toplevel-comment a").click(function() {
        $('#newcomment input[name="parent_id"]').val('');
        $('#newcomment input[name="comment_edit_id"]').val('');
        $("#comment-submit").val("Post comment"); // i18n gotcha
        $(this).parent().after($("#newcomment"));
        $(this).parent().addClass('hidden');
        $("#newcomment textarea").focus();
        return false;
    });

    $(".comments .comment-delete").click(function() {
        var cfooter = $(this).parent();
        $('#delcomment input[name="comment_id"]').val(cfooter.attr('data-id'));
        $("#delcomment").removeClass('hidden').hide().insertAfter(cfooter).slideDown("fast");
        return false;
    });

    $("#comment-delete-cancel").click(function() {
        $("#delcomment").slideUp("fast");
        return false;
    });

    $(".comments .comment-edit").click(function() {
        var cfooter = $(this).parent();
        var cid = cfooter.attr('data-id');
        $("#newcomment textarea").val("Loading..."); // i18n gotcha
        $.getJSON(pageURL+'/comments/'+cid+'/json', function(data) {
            $("#newcomment textarea").val(data.message);
            });
        $('#newcomment input[name="parent_id"]').val('');
        $('#newcomment input[name="comment_edit_id"]').val(cid);
        $("#toplevel-comment").removeClass('hidden');
        $("#comment-submit").val("Save changes"); // i18n gotcha
        cfooter.after($("#newcomment"));
        $("#newcomment textarea").focus();
        return false;
    });
}

// ROT13 link handler
$(function() {
  $("a.rot13").each(function() {
    if ($(this).attr('data-href')) {
      var decoded = $(this).attr('data-href').replace(/[a-zA-Z]/g, function(c) {
        return String.fromCharCode((c<="Z"?90:122)>=(c=c.charCodeAt(0)+13)?c:c-26);
        });
      $(this).attr('href', decoded);
      $(this).removeAttr('data-href');
      $(this).removeClass('rot13');
    }
  });
});

// Enable markdown previews
markdownPreview();
