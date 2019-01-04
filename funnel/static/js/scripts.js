
window.Talkfunnel = {};
window.Talkfunnel.Config = {
  defaultLatitude: "12.961443",
  defaultLongitude: "77.64435000000003"
};

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
  animateScrollTo: function(offsetY) {
    $('html,body').animate({scrollTop: offsetY}, 500);
  },
  smoothScroll: function() {
    $('a.smooth-scroll').on('click', function(event) {
      event.preventDefault();
      Talkfunnel.Utils.animateScrollTo($(this.hash).offset().top);
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
}

window.Talkfunnel.Video = {
  /* Takes argument
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (extractYoutubeId).
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
    Ractive.DEBUG = false;

    this.config = config;
    this.checkinQ = new Talkfunnel.Queue(config.eventName + "-" + "checkin-queue");;
    this.cancelcheckinQ = new Talkfunnel.Queue(config.eventName + "-" + "cancelcheckin-queue");

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

window.Talkfunnel.Schedule = {
  renderScheduleTable: function() {
    Ractive.DEBUG = false;
    var schedule = this;

    scheduleUI = new Ractive({
      el: schedule.config.divElem,
      template: schedule.config.scriptTemplate,
      data: {
        schedules: schedule.config.scheduleTable,
        rowWidth: Object.keys(schedule.config.rooms).length,
        rowHeight: '30',
        timeSlotWidth: '75',
        rowBorder: '1',
        activeTab: Object.keys(schedule.config.rooms)[0],
        width: $(window).width(),
        height: $(window).height(),
        modalHtml: '',
        headerHeight: '',
        pageUrl: location.href,
        getTimeStr: function(time) {
          return new Date(parseInt(time, 10)).toLocaleTimeString().replace(/(.*)\D\d+/, '$1');
        },
        getColumnWidth: function(columnType) {
          if(columnType === 'header' || this.get('width') > 991) {
            return (this.get('timeSlotWidth')/this.get('rowWidth'));
          } else {
            return 0;
          }
        },
        hasActiveRoom: function(session) {
          return session.rooms[this.get('activeTab')].hasOwnProperty('talks');
        },
        removeImg: function(descriptionHtml) {
          return descriptionHtml.replace(/<img[^>]*>/g,"");
        }
      },
      toggleTab: function(event, room) {
        var ractiveUI = this;
        if(ractiveUI.get('width') < 992) {
          event.original.preventDefault();
          ractiveUI.set('activeTab', room);
          Talkfunnel.Utils.animateScrollTo($(event.node.parentElement).offset().top - ractiveUI.get('headerHeight'));
        }
      },
      handleBrowserHistory: function() {
        var ractiveUI = this;
        // On closing modal, update browser history
        $("#session-modal").on($.modal.CLOSE, function() {
          ractiveUI.set('modalHtml', '');
          window.history.pushState('', '', ractiveUI.get('pageUrl'));
        });
        // Event listener for back key press since opening modal update browser history
        $(window).on('popstate', function (event) {
          if(ractiveUI.get('modalHtml')) {
            $.modal.close();
          } else if(history.state) {
            // Open the modal with previous session viewed
            ractiveUI.openModal(history.state.html, history.state.backPage);
          }
        });
      },
      openModal: function(sessionHtml, backPage) {
        var ractiveUI = this;
        ractiveUI.set('modalHtml', sessionHtml);
        $("#session-modal").modal('show');
        window.history.pushState({html: sessionHtml, backpage: backPage}, '', backPage);
      },
      showSessionModal: function(event, activeSession) {
        var ractiveUI = this;
        var sessionModalUrl, sessionUrl, backPage;
        sessionModalUrl = event ? ractiveUI.get(event.keypath + '.talks.modal_url') : activeSession.modal_url;
        sessionUuid = event ? ractiveUI.get(event.keypath + '.talks.url_name_suuid') : activeSession.url_name_suuid;
        backPage = ractiveUI.get('pageUrl') + '/' + sessionUuid;
        if(sessionModalUrl) {
          $.ajax({
            url: sessionModalUrl,
            type: 'GET',
            success: function(sessionHtml) {
              ractiveUI.openModal(sessionHtml, backPage);
            },
            error: function(response) {
              toastr.error('There was a problem in contacting the server. Please try again later.');
            }
          });
        }
      },
      disableScroll: function(event) {
        event.original.preventDefault();
        location.hash = event.node.id;
        Talkfunnel.Utils.animateScrollTo($(location.hash).offset().top - this.get('headerHeight'));
      },
      handleBrowserResize: function() {
        var ractiveUI = this;
        $(window).resize(function() {
          ractiveUI.set('width', $(window).width());
          ractiveUI.set('height', $(window).height());
        });
      },
      animateWindowScrollWithHeader: function() {
        var ractiveUI = this;
        var hash;
        ractiveUI.set('headerHeight', 2 * $('.schedule__row--sticky').height());
        ractiveUI.set('pathName', location.pathname);
        if(location.pathname === ractiveUI.get('pathName') && location.hash) {
          hash = location.hash.indexOf('/') != -1 ? location.hash.substring(0, location.hash.indexOf('/')) : location.hash;
          Talkfunnel.Utils.animateScrollTo($(hash).offset().top - ractiveUI.get('headerHeight'));
        }
      },
      oncomplete: function() {
        var ractiveUI = this;
        var activeSession = schedule.config.active_session;
        if(activeSession) {
          // Open session modal
          var paths = location.href.split('/');
          paths.pop()
          ractiveUI.set('pageUrl', paths.join('/'));
          ractiveUI.showSessionModal('', activeSession);
          // Scroll page to session
          Talkfunnel.Utils.animateScrollTo($("#" + activeSession.url_name_suuid).offset().top - ractiveUI.get('headerHeight'));
        }

        ractiveUI.animateWindowScrollWithHeader();
        ractiveUI.handleBrowserResize();
        ractiveUI.handleBrowserHistory();
      }
    });
  },
  addSessionToSchedule: function (session) {
    var schedule = this;
    schedule.config.scheduled.forEach(function(session) {
      if(!session.room_scoped_name) {
        session.room_scoped_name = Object.keys(schedule.config.rooms)[0];
      }
      schedule.config.scheduleTable[session.eventDay]['sessions'][session.startTime].showLabel = true;
      schedule.config.scheduleTable[session.eventDay]['sessions'][session.startTime].rooms[session.room_scoped_name].talks = session;
    });
  },
  createScheduleTable: function(argument) {
    var schedule = this;
    Object.keys(schedule.config.scheduleTable).forEach(function(eventDay) {
      var slots = {};
      var sessionSlots = schedule.config.scheduleTable[eventDay].startTime;
      while(sessionSlots < schedule.config.scheduleTable[eventDay].endTime) {
        slots[sessionSlots] = {showLabel: false, rooms: JSON.parse(JSON.stringify(schedule.config.rooms))};
        sessionSlots = new Date(sessionSlots);
        sessionSlots = sessionSlots.setMinutes(sessionSlots.getMinutes() + schedule.config.slotInterval);
      };
      schedule.config.scheduleTable[eventDay].sessions = JSON.parse(JSON.stringify(slots));
    });
  },
  getEventDuration: function() {
    var schedule = this;
    schedule.config.scheduled.forEach(function(session) {
      session.startTime = Talkfunnel.Schedule.Utils.getTime(session.start);
      session.endTime = Talkfunnel.Schedule.Utils.getTime(session.end);
      session.eventDay = Talkfunnel.Schedule.Utils.getEventDate(session.start);
      session.duration = Talkfunnel.Schedule.Utils.getDuration(session.end, session.start);
      schedule.config.scheduleTable[session.eventDay].startTime = schedule.config.scheduleTable[session.eventDay].startTime && schedule.config.scheduleTable[session.eventDay].startTime < new Date(session.start).getTime() ? schedule.config.scheduleTable[session.eventDay].startTime : new Date(session.start).getTime();
      schedule.config.scheduleTable[session.eventDay].endTime = schedule.config.scheduleTable[session.eventDay].endTime > new Date(session.end).getTime() ? schedule.config.scheduleTable[session.eventDay].endTime : new Date(session.end).getTime();
    });
  },
  getEventDays: function() {
    var difference = (new Date(this.config.toDate) - new Date(this.config.fromDate))/ (1000 * 3600 * 24);    var eventDays = {};
    var day = Talkfunnel.Schedule.Utils.getEventDate(this.config.fromDate);
    eventDays[day] = {dateStr: Talkfunnel.Schedule.Utils.getDateString(this.config.fromDate), talks: {},
      startTime: 0, endTime: 0, rooms: JSON.parse(JSON.stringify(this.config.rooms))};
    while(difference > 0) {
      nextDay = new Date();
      nextDay.setDate(day + 1);
      day = nextDay.getDate();
      eventDays[day] = {dateStr: Talkfunnel.Schedule.Utils.getDateString(nextDay), talks: {},
        startTime: 0, endTime: 0, rooms: JSON.parse(JSON.stringify(this.config.rooms))};
      difference--;
    };
    // To create a copy and not a reference
    this.config.scheduleTable = JSON.parse(JSON.stringify(eventDays));
    return;
  },
  init: function(config) {
    this.config = config;
    Talkfunnel.Schedule.getEventDays();
    Talkfunnel.Schedule.getEventDuration();
    Talkfunnel.Schedule.createScheduleTable();
    Talkfunnel.Schedule.addSessionToSchedule();
    Talkfunnel.Schedule.renderScheduleTable();
  },
  Utils: {
    getEventDate: function(eventDate) {
      var date =  new Date(eventDate);
      return date.getDate();
    },
    getTime: function(dateTime) {
      return new Date(dateTime).getTime()
    },
    getDateString: function(eventDate) {
      return new Date(eventDate).toDateString();
    },
    getDuration: function(endDate, startDate) {
      var duration = new Date(endDate) - new Date(startDate);
      // Convert to minutes and multiply by slotInterval
      return duration/1000/60/Talkfunnel.Schedule.config.slotInterval;
    }
  }
};

window.Talkfunnel.EmbedMap = {
  init: function(config) {
    if(typeof window.L === "undefined") {
      window.setTimeout(initLeaflets, 5000);
      return;
    }

    var $container = $(config.mapElem),
      defaults = {
        zoom: 17,
        marker: [Talkfunnel.Config.defaultLatitude, Talkfunnel.Config.defaultLongitude],
        label: null,
        maxZoom: 18,
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
        subdomains: ['a','b','c'],
        scrollWheelZoom: false,
        dragging: false,
      },
      args,
      options,
      map,
      marker;
    $container.empty();

    args = $container.data();
    if (args.markerlat && args.markerlng) { args.marker = [args.markerlat,args.markerlng]; }
    options = $.extend({}, defaults, args);

    map = new L.Map($container[0], {
        center: options.center || options.marker
        , zoom: options.zoom
        , scrollWheelZoom: options.scrollWheelZoom
        , dragging: options.dragging
    });

    var tileLayer = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
    L.tileLayer(tileLayer, {
        maxZoom: options.maxZoom
        , attribution: options.attribution
        , subdomains: options.subdomains
    }).addTo(map);


    if (!args.tilelayer) {
      marker = new L.marker(options.marker).addTo(map);
      if (options.label) marker.bindPopup(options.label).openPopup();
    }
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
