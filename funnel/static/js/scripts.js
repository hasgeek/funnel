
window.Talkfunnel = {};

window.Talkfunnel.Store = {
  //Local storage can only save strings, so value is converted into strings and stored.
  add: function(key, value) {
    return localStorage.setItem(key, JSON.stringify(value));
  },
  //Reads from LocalStorage.
  read: function(key) {
    return JSON.parse(localStorage.getItem(key));
  }
};

window.Talkfunnel.Queue = function(queueName) {
  this.queueName = queueName;

  //Adds a participant_id to queue
  this.enqueue = function(participant_id) {
    var participantList = window.Talkfunnel.Store.read(this.queueName) || [];
    if (participantList.indexOf(participant_id) === -1) {
      participantList.push(participant_id);
      return window.Talkfunnel.Store.add(this.queueName, participantList);
    }
  };

  //Reads and returns all items from queue
  //Returns undefined when queue is empty or not defined
  this.readAll = function() {
    var participantList = window.Talkfunnel.Store.read(this.queueName);
    if (participantList && participantList.length) {
      return participantList;
    }
  };

  //Removes item from queue and returns true
  //Returns undefined when item not present in queue
  this.dequeue = function(participant_id) {
    var participantList = window.Talkfunnel.Store.read(this.queueName);
    var index = participantList ? participantList.indexOf(participant_id) : -1;
    if (index !== -1) {
      //Remove item from queue and add updated queue to localStorage
      participantList.splice(index, 1);
      window.Talkfunnel.Store.add(this.queueName, participantList);
      return participant_id;
    }
  };

  //updateQueue: If participant in "checkin-queue" has already been checked-in then it is removed from checkin queue
  this.updateQueue = function(participants) {
    var queue = this;
    var participantIDs = queue.readAll();
    if (participantIDs) {
      participantIDs.forEach(function(participantID) {
        if (queue.queueName.indexOf("cancelcheckin-queue") > -1) {
          if (!participants[participantID].checked_in) {
            //Participant's check-in has been cancelled so remove from 'cancelcheckin-queue'
            queue.dequeue(participantID);
          }
          else {
            $('#' + participantID).find('.js-loader').show();
          }
        }
        else {
          if (participants[participantID].checked_in) {
            //Participant has been checked-in so remove from 'checkin-queue'
            queue.dequeue(participantID);
          }
          else {
            $('#' + participantID).find('.js-loader').show();
          }
        }
      });
    }
  };
};

window.Talkfunnel.ParticipantTable = {
  init: function(config, checkinQ, cancelcheckinQ) {
    this.Config = {
      checkinUrl: config.checkinUrl,
      participantlistUrl: config.participantlistUrl
    };
    this.checkinQ = checkinQ;
    this.cancelcheckinQ = cancelcheckinQ;

    Ractive.DEBUG = false;

    this.participantTableCount = new Ractive({
      el: '#participants-count',
      template: '#participants-count-template',
      data: {
        total_participants: '',
        total_checkedin: ''
      }
    });

    this.participantTableContent = new Ractive({
      el: '#participants-table-content',
      template: '#participant-row',
      data: {
        participants: '',
        getCsrfToken: function() {
          return $('meta[name="csrf-token"]').attr('content');
        },
        getBadgeUrl: function(pid) {
          return config.badgeUrl.replace('participant-id',pid);
        },
        getEditUrl: function(pid) {
          return config.editUrl.replace('participant-id',pid);
        },
        getCheckinUrl: function() {
          return config.checkinUrl;
        }
      }
    });
  },
  update: function() {
    var participantTable = this;
    
    $.ajax({
      type: 'GET',
      url: participantTable.Config.participantlistUrl,
      timeout: 5000,
      dataType: 'json',
      success: function(data) {
        participantTable.participantTableCount.set({
          total_participants: data.total_participants,
          total_checkedin: data.total_checkedin
        });
        participantTable.participantTableContent.set('participants', data.participants).then(function() {
          $('.js-loader').hide();
          var participants = tohashMap(data.participants, "pid");
          participantTable.checkinQ.updateQueue(participants);
          participantTable.cancelcheckinQ.updateQueue(participants);
        });
        $('.footable').trigger('footable_redraw');
      }
    });
  },
  handleCheckIn: function() {
    var participantTable = this;

    $('#participants-table-content').on('submit', '.checkin_form', function(event) {
      event.preventDefault();
      var formValues = {};
      $(this).serializeArray().map(function(obj) {
        formValues[obj.name] = obj.value;
      });
      if (formValues["checkin"] === "t") {
        participantTable.checkinQ.enqueue(formValues["pid"]);
      }
      else {
        participantTable.cancelcheckinQ.enqueue(formValues["pid"]);
      }
      $(this).find('.js-loader').show();
    });
  },
  handleAbortCheckIn: function() {
    var participantTable = this;

    $('#participants-table-content').on('click', '.js-abort', function(event) {
      event.preventDefault();
      var participantID = $(this).siblings('input[name="pid"]').val();
      var checkinStatus = $(this).siblings('input[name="checkin"]').val();

      if (checkinStatus === "t") {
        // Case 1: On abort, participantID is removed from "checkin-queue" if present.
        // Case 2: On abort, if participantID is not present in the "checkin-queue" it implies check-in request has been sent to server, so check-in has to be cancelled, hence add it to "cancelcheckin-queue".
        if (!participantTable.checkinQ.dequeue(participantID)) {
          participantTable.cancelcheckinQ.enqueue(participantID);
        }
      }
      else{
        if (!participantTable.cancelcheckinQ.dequeue(participantID)) {
          participantTable.checkinQ.enqueue(participantID);
        }
      }
      //Hide loader and abort
      $('#' + participantID).find('.js-loader').hide();
    });
  },
  postCheckinStatus: function(participantIDs, action) {
    var participantTable = this;

    var formValues = $.param({"pid":participantIDs}, true);
    if (action) {
      formValues += "&checkin=t";
    }
    formValues += "&csrf_token=" + $("meta[name='csrf-token']").attr('content');
    $.ajax({
      type: 'POST',
      url:  participantTable.Config.checkinUrl,
      data : formValues,
      timeout: 5000,
      dataType: "json",
      success: function(data) {
        if (data.checked_in) {
          data.participant_ids.forEach(function(participant_id) {
            participantTable.checkinQ.dequeue(participant_id);
          });
        }
        else {
          data.participant_ids.forEach(function(participant_id) {
            participantTable.cancelcheckinQ.dequeue(participant_id);
          });
        }
      }
    });
  },
  processQueues: function() {
    var participantTable = this;

    var participantIDs = participantTable.checkinQ.readAll();
    if (participantIDs) {
      participantTable.postCheckinStatus(participantIDs, true);
    }

    participantIDs = participantTable.cancelcheckinQ.readAll();
    if (participantIDs) {
      participantTable.postCheckinStatus(participantIDs, false);
    }
  }
};

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
