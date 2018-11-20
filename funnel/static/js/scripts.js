
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
  },
  collapse: function() {
    $('.collapsible__header').click(function() {
      $(this).find('.collapsible__icon').toggleClass('mui--hide');
      $(this).next('.collapsible__body').slideToggle();
    });
  },
  smoothScroll: function(className) {
    $(className).on('click', function(event) {
      if (this.hash !== "") {
        event.preventDefault();
        var section = this.hash;
        $('html, body').animate({
          scrollTop: $(section).offset().top
        }, 800);
      }
    });
  }
}

window.Talkfunnel.Comments = {
  init: function(pageURL) {
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
}

window.Talkfunnel.Video = {
  /* Takes argument 
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (extractYoutubeId) .  
    The videoID is then used to generate the iframe html. 
    The generated iframe is added to the video container element.
  */
  embedIframe: function(videoWrapper, videoUrl) {
    var videoId, videoEmbedUrl, noVideoUrl;
    videoId = this.extractYoutubeId(videoUrl);
    if(videoId) {
      videoEmbedUrl = '<iframe id="youtube_player" src="//www.youtube.com/embed/' + videoId + '" frameborder="0" allowfullscreen></iframe>';
      videoWrapper.innerHTML = videoEmbedUrl;
    }
  },
  extractYoutubeId: function(url) {
    var regex = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*/;
    var exp = url.match(regex);
    if (exp && exp[7].length == 11) {
      return exp[7];
    }
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

window.Talkfunnel.TicketWidget = {
  init: function(config) {
    var url;
    if (config.boxofficeUrl.slice(-1) === '/') {
      url = config.boxofficeUrl + "boxoffice.js";
    } else {
      url = config.boxofficeUrl + "/boxoffice.js";
    }
    $.get({
      url: url,
      crossDomain: true,
      timeout: 8000,
      retries: 5,
      retryInterval: 8000,
      success: function(data) {
        var boxofficeScript = document.createElement('script');
        boxofficeScript.innerHTML = data.script;
        document.getElementsByTagName('body')[0].appendChild(boxofficeScript);
      },
      error: function(response) {
        var ajaxLoad = this;
        ajaxLoad.retries -= 1;
        var errorMsg;
        if (response.readyState === 4) {
          errorMsg = "Server error, please try again later.";
          $(config.widgetElem).html(errorMsg);
        }
        else if (response.readyState === 0) {
          if (ajaxLoad.retries < 0) {
            if(!navigator.onLine) {
              errorMsg = "Unable to connect. There is no network!";
            }
            else {
              errorMsg = "<p>Unable to connect. If you are behind a firewall or using any script blocking extension (like Privacy Badger), please ensure your browser can load boxoffice.hasgeek.com, api.razorpay.com and checkout.razorpay.com .</p>";
            }
            $(config.widgetElem).html(errorMsg);
          } else {
            setTimeout(function() {
              $.get(ajaxLoad);
            }, ajaxLoad.retryInterval);
          }
        }
      }
    });

    window.addEventListener('onBoxofficeInit', function (e) {
      window.Boxoffice.init({
        org: config.org,
        itemCollection: config.itemCollectionId,
        paymentDesc: config.itemCollectionTitle,

      });
    }, false);
  }
};

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
