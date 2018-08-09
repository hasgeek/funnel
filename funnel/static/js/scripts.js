
window.Talkfunnel = {};

window.Talkfunnel.Utils = {
  //convert array of objects into hashmap
  tohashMap: function(objectArray, key) {
    var hashMap = {};
    objectArray.forEach(function(obj) {
      hashMap[obj[key]] = obj;
    });
    return hashMap;
  },
  findLoopIndex: function(objectArray, key, search) {
    for(var index = 0; index < objectArray.length; index++) {
      if(objectArray[index][key] === search) {
        break;
      }
    }
    return index;
  }
}

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

  //Adds a participantId to queue
  this.enqueue = function(participantId) {
    var participantList = window.Talkfunnel.Store.read(this.queueName) || [];
    if (participantList.indexOf(participantId) === -1) {
      participantList.push(participantId);
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
  this.dequeue = function(participantId) {
    var participantList = window.Talkfunnel.Store.read(this.queueName);
    var index = participantList ? participantList.indexOf(participantId) : -1;
    if (index !== -1) {
      //Remove item from queue and add updated queue to localStorage
      participantList.splice(index, 1);
      window.Talkfunnel.Store.add(this.queueName, participantList);
      return participantId;
    }
  };

  //updateQueue: If participant in "checkin-queue" has already been checked-in then it is removed from checkin queue
  this.updateQueue = function(participantsHashMap) {
    var queue = this;
    var participantIDs = queue.readAll();
    var participants = Talkfunnel.ParticipantTable.list.get('participants');
    if (participantIDs) {
      participantIDs.forEach(function(participantID) {
        if (queue.queueName.indexOf("cancelcheckin-queue") > -1) {
          if (!participantsHashMap[participantID].checked_in) {
            //Participant's check-in has already been cancelled so remove from 'cancelcheckin-queue'
            queue.dequeue(participantID);
          }
          else {
            var index = Talkfunnel.Utils.findLoopIndex(participants, 'pid', participantID);
            Talkfunnel.ParticipantTable.list.set('participants.' + index + '.submitting', true);
          }
        }
        else {
          if (participantsHashMap[participantID].checked_in) {
            //Participant has been checked-in so remove from 'checkin-queue'
            queue.dequeue(participantID);
          }
          else {
            var index = Talkfunnel.Utils.findLoopIndex(participants, 'pid', participantID);
            Talkfunnel.ParticipantTable.list.set('participants.' + index + '.submitting', true);
          }
        }
      });
    }
  };
};

window.Talkfunnel.ParticipantTable = {
  init: function(config) {
    this.config = config;
    this.checkinQ = new Talkfunnel.Queue(config.eventName + "-" + "checkin-queue");;
    this.cancelcheckinQ = new Talkfunnel.Queue(config.eventName + "-" + "cancelcheckin-queue");

    Ractive.DEBUG = false;

    this.count = new Ractive({
      el: '#participants-count',
      template: '#participants-count-template',
      data: {
        total_participants: '',
        total_checkedin: ''
      }
    });

    this.list = new Ractive({
      el: '#participants-table-content',
      template: '#participant-row',
      data: {
        participants: '',
        getCsrfToken: function() {
          return $('meta[name="csrf-token"]').attr('content');
        },
        getBadgeUrl: function(pid) {
          return Talkfunnel.ParticipantTable.config.badgeUrl.replace('participant-id',pid);
        },
        getEditUrl: function(pid) {
          return Talkfunnel.ParticipantTable.config.editUrl.replace('participant-id',pid);
        },
        getCheckinUrl: function() {
          return Talkfunnel.ParticipantTable.config.checkinUrl;
        }
      },
      handleCheckIn: function(event, checkin) {
        event.original.preventDefault();
        var participantID = this.get(event.keypath + '.pid');
        if (checkin) {
          // Add participant id to checkin queue
          Talkfunnel.ParticipantTable.checkinQ.enqueue(participantID);
        } else {
          Talkfunnel.ParticipantTable.cancelcheckinQ.enqueue(participantID);
        }
        // Show the loader icon
        this.set(event.keypath + '.submitting', true);
      },
      handleAbortCheckIn: function(event, checkin) {
        event.original.preventDefault();
        var participantID = this.get(event.keypath + '.pid');
        if(checkin) {
          Talkfunnel.ParticipantTable.checkinQ.dequeue(participantID)
          Talkfunnel.ParticipantTable.cancelcheckinQ.enqueue(participantID);
        } else {
          Talkfunnel.ParticipantTable.cancelcheckinQ.dequeue(participantID)
          Talkfunnel.ParticipantTable.checkinQ.enqueue(participantID);
        }
        // Hide the loader icon
        this.set(event.keypath + '.submitting', false);
      },
      updateList: function() {
        $.ajax({
          type: 'GET',
          url: Talkfunnel.ParticipantTable.config.participantlistUrl,
          timeout: 5000,
          dataType: 'json',
          success: function(data) {
            Talkfunnel.ParticipantTable.count.set({
              total_participants: data.total_participants,
              total_checkedin: data.total_checkedin
            });
            Talkfunnel.ParticipantTable.list.set('participants', data.participants).then(function() {
              var participants = Talkfunnel.Utils.tohashMap(data.participants, "pid");
              Talkfunnel.ParticipantTable.checkinQ.updateQueue(participants);
              Talkfunnel.ParticipantTable.cancelcheckinQ.updateQueue(participants);
            });
            // $('.footable').trigger('footable_redraw');
          }
        });
      },
      onrender: function() {
        this.updateList();
    
        //Read 'checkin-queue' and 'cancelcheckin-queue' every 8 seconds and batch post check-in/cancel check-in status to server
        setInterval(function() { Talkfunnel.ParticipantTable.processQueues(); }, 8000);

        //Get participants data from server every 15 seconds
        setInterval(function() { Talkfunnel.ParticipantTable.list.updateList(); }, 15000);
      }
    });
  },
  processQueues: function() {
    var participantIDs = Talkfunnel.ParticipantTable.checkinQ.readAll();
    if (participantIDs) {
      Talkfunnel.ParticipantTable.postCheckinStatus(participantIDs, true);
    }

    participantIDs = Talkfunnel.ParticipantTable.cancelcheckinQ.readAll();
    if (participantIDs) {
      Talkfunnel.ParticipantTable.postCheckinStatus(participantIDs, false);
    }
  },
  postCheckinStatus: function(participantIDs, action) {
    var formValues = $.param({"pid":participantIDs}, true);
    if (action) {
      formValues += "&checkin=t";
    } else {
      formValues += "&checkin=f";
    }
    formValues += "&csrf_token=" + $("meta[name='csrf-token']").attr('content');
    $.ajax({
      type: 'POST',
      url:  Talkfunnel.ParticipantTable.config.checkinUrl,
      data : formValues,
      timeout: 5000,
      dataType: "json",
      success: function(data) {
        if (data.checked_in) {
          data.participant_ids.forEach(function(participantId) {
            Talkfunnel.ParticipantTable.checkinQ.dequeue(participantId);
          });
        }
        else {
          data.participant_ids.forEach(function(participantId) {
            Talkfunnel.ParticipantTable.cancelcheckinQ.dequeue(participantId);
          });
        }
      }
    });
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
  $(".comment .js-collapse").click(function() {
    $(this).addClass('mui--hide');
    $(this).siblings('.js-uncollapse').removeClass('mui--hide');
    $(this).parent().siblings('.comment--body').slideUp("fast");
    $(this).parent().siblings('.comment--children').slideUp("fast");
    return false;
  });

  $(".comment .js-uncollapse").click(function() {
    $(this).addClass('mui--hide');
    $(this).siblings('.js-collapse').removeClass('mui--hide');
    $(this).parent().siblings('.comment--body').slideDown("fast");
    $(this).parent().siblings('.comment--children').slideDown("fast");
    return false;
  });

  $(".comment .js-comment-reply").click(function() {
    var cfooter = $(this).parent();
    $('#comment-form input[name="parent_id"]').val(cfooter.attr('data-id'));
    $('#comment-form  input[name="comment_edit_id"]').val('');
    $("#toplevel-comment").removeClass('mui--hide');
    $("#comment-submit").val("Reply"); // i18n gotcha
    cfooter.after($("#comment-form"));
    $("#comment-form textarea").focus();
    return false;
  });

  $("#toplevel-comment a").click(function() {
    $('#comment-form  input[name="parent_id"]').val('');
    $('#comment-form  input[name="comment_edit_id"]').val('');
    $("#comment-submit").val("Post comment"); // i18n gotcha
    $(this).parent().after($("#comment-form"));
    $(this).parent().addClass('mui--hide');
    $("#comment-form textarea").focus();
    return false;
  });

  $(".comment .js-comment-delete").click(function() {
    var cfooter = $(this).parent();
    $('#delcomment input[name="comment_id"]').val(cfooter.attr('data-id'));
    $("#delcomment").removeClass('mui--hide').hide().insertAfter(cfooter).slideDown("fast");
    return false;
  });

  $("#comment-delete-cancel").click(function() {
    $("#delcomment").slideUp("fast");
    return false;
  });

  $(".comment .js-comment-edit").click(function() {
    var cfooter = $(this).parent();
    var cid = cfooter.attr('data-id');
    $("#comment-form textarea").val("Loading..."); // i18n gotcha
    $.getJSON(pageURL+'/comments/'+cid+'/json', function(data) {
      $("#comment-form textarea").val(data.message);
    });
    $('#comment-form input[name="parent_id"]').val('');
    $('#comment-form input[name="comment_edit_id"]').val(cid);
    $("#toplevel-comment").removeClass('mui--hide');
    $("#comment-submit").val("Save changes"); // i18n gotcha
    cfooter.after($("#comment-form"));
    $("#comment-form textarea").focus();
    return false;
  });
}

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
