
window.Talkfunnel = {};

if (Modernizr.localstorage) {
  window.Talkfunnel.Store = {};

  //Local storage can only save strings, so value is converted into strings and stored.
  window.Talkfunnel.Store.add = function(key, value) {
    return localStorage.setItem(key, JSON.stringify(value));
  };

  //Reads from LocalStorage.
  window.Talkfunnel.Store.read = function(key) {
    return JSON.parse(localStorage.getItem(key));
  };

  window.Talkfunnel.Queue = function(queueName) {
    this.queueName = queueName;

    //Adds a participant_id to queue
    this.enqueue = function(participant_id) {
      var participantList = window.Talkfunnel.Store.read(this.queueName) || [];
      if(participantList.indexOf(participant_id) === -1) {
        participantList.push(participant_id);
        return window.Talkfunnel.Store.add(this.queueName, participantList);
      }
    };

    //Reads and returns all items from queue
    //Returns undefined when queue is empty or not defined
    this.readAll = function() {
      var participantList = window.Talkfunnel.Store.read(this.queueName);
      if(participantList && participantList.length) {
        return participantList;
      }
    };

    //Removes item from queue and returns true
    //Returns undefined when item not present in queue
    this.dequeue = function(participant_id) {
      var participantList = window.Talkfunnel.Store.read(this.queueName);
      var index = participantList ? participantList.indexOf(participant_id) : -1;
      if(index !== -1) {
        //Remove item from queue and add updated queue to localStorage
        participantList.splice(index, 1);
        window.Talkfunnel.Store.add(this.queueName, participantList);
        return participant_id;
      }
    };
  }
}

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

window.TableSearch = function(tableId){
  // a little library that takes a table id
  // and provides a method to search the table's rows for a given query.
  // the row's td must contain the class 'js-searchable' to be considered
  // for searching.
  // Eg:
  // var tableSearch = new TableSearch('tableId');
  // var hits = tableSearch.searchRows('someQuery');
  // 'hits' is a list of ids of the table's rows which contained 'someQuery'
  this.tableId = tableId;
  this.rowData = [];
  this.allMatchedIds = [];
};

window.TableSearch.prototype.getRows = function(){
  return $('#' + this.tableId +' tbody tr');
};

window.TableSearch.prototype.setRowData = function(rowD){
  // Builds a list of objects and sets it the object's rowData
  var rowMap = [];
  $.each(this.getRows(), function(rowIndex, row){
    rowMap.push({
      'rid': '#' + $(row).attr('id'),
      'text': $(row).find('td.js-searchable').text().toLowerCase()
    });
  });
  this.rowData = rowMap;
};

window.TableSearch.prototype.setAllMatchedIds = function(ids) {
  this.allMatchedIds = ids;
};

window.TableSearch.prototype.searchRows = function(q){
  // Search the rows of the table for a supplied query.
  // reset data collection on first search or if table has changed
  if (this.rowData.length !== this.getRows().length) {
    this.setRowData();
  }
  // return cached matched ids if query is blank
  if (q === '' && this.allMatchedIds.length !== 0) {
    return this.allMatchedIds;
  }
  var matchedIds = [];
  for (var i = this.rowData.length - 1; i >= 0; i--) {
    if (this.rowData[i].text.indexOf(q.toLowerCase()) !== -1) {
      matchedIds.push(this.rowData[i]['rid']);
    }
  }
  // cache ids if query is blank
  if (q === '') {
    this.setAllMatchedIds(matchedIds);
  }
  return matchedIds;
};

//convert array of objects into hashmap
function tohashMap(objectArray, key) {
  var hashMap = {};
  objectArray.forEach(function(obj) {
    hashMap[obj[key]] = obj;
  });
  return hashMap;
}
