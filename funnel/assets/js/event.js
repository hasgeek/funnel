import {Utils, TableSearch} from './util';
import Ractive from "ractive";

const Store = {
  // Local storage can only save strings, so value is converted into strings and stored.
  add(key, value) {
    return localStorage.setItem(key, JSON.stringify(value));
  },
  // Reads from LocalStorage.
  read(key) {
    return JSON.parse(localStorage.getItem(key));
  },
};

const Queue = function(queueName) {
  this.queueName = queueName;

  // Adds a participantId to queue
  this.enqueue = function(participantId) {
    let participantList = Store.read(this.queueName) || [];
    if (participantList.indexOf(participantId) === -1) {
      participantList.push(participantId);
      return Store.add(this.queueName, participantList);
    }
    else {
      return false;
    }
  };

  // Reads and returns all items from queue
  // Returns undefined when queue is empty or not defined
  this.readAll = function() {
    let participantList = Store.read(this.queueName);
    if (participantList && participantList.length) {
      return participantList;
    } else {
      return false;
    }
  };

  // Removes item from queue and returns true
  // Returns undefined when item not present in queue
  this.dequeue = function(participantId) {
    var participantList = Store.read(this.queueName);
    var index = participantList ? participantList.indexOf(participantId) : -1;
    if (index !== -1) {
      // Remove item from queue and add updated queue to localStorage
      participantList.splice(index, 1);
      Store.add(this.queueName, participantList);
      return participantId;
    } else {
      return false;
    }
  };

  /* updateQueue: If participant in "checkin-queue" has already been checked-in 
  then it is removed from checkin queue */
  this.updateQueue = function(participantsHashMap, ParticipantList) {
    let queue = this;
    let participantIDs = queue.readAll();
    let participants = ParticipantList.get('participants');
    if (participantIDs) {
      participantIDs.forEach(function(participantID) {
        if (queue.queueName.indexOf("cancelcheckin-queue") > -1) {
          if (!participantsHashMap[participantID].checked_in) {
            /* Participant's check-in has already been cancelled so remove 
            from 'cancelcheckin-queue' */
            queue.dequeue(participantID);
          }
          else {
            let index = Utils.findLoopIndex(participants, 'pid', participantID);
            ParticipantList.set('participants.' + index + '.submitting', true);
          }
        }
        else {
          if (participantsHashMap[participantID].checked_in) {
            // Participant has been checked-in so remove from 'checkin-queue'
            queue.dequeue(participantID);
          }
          else {
            let index = Utils.findLoopIndex(participants, 'pid', participantID);
            ParticipantList.set('participants.' + index + '.submitting', true);
          }
        }
      });
    }
  };
};

const ParticipantTable = {
  init: function({badgeUrl, editUrl, checkinUrl, participantlistUrl, eventName}) {
    Ractive.DEBUG = false;

    let count = new Ractive({
      el: '#participants-count',
      template: '#participants-count-template',
      data: {
        total_participants: '',
        total_checkedin: ''
      }
    });

    let list = new Ractive({
      el: '#participants-table-content',
      template: '#participant-row',
      data: {
        participants: '',
        checkinUrl: checkinUrl,
        checkinQ: new Queue(`${eventName}-checkin-queue`),
        cancelcheckinQ: new Queue(`${eventName}-cancelcheckin-queue`),
        getCsrfToken() {
          return $('meta[name="csrf-token"]').attr('content');
        },
        getBadgeUrl(pid) {
          return badgeUrl.replace('participant-id', pid);
        },
        getEditUrl(pid) {
          return editUrl.replace('participant-id', pid);
        },
        getCheckinUrl() {
          return checkinUrl;
        }
      },
      handleCheckIn(event, checkin) {
        event.original.preventDefault();
        let participantID = this.get(event.keypath + '.pid');
        if (checkin) {
          // Add participant id to checkin queue
          this.get('checkinQ').enqueue(participantID);
        } else {
          this.get('cancelcheckinQ').enqueue(participantID);
        }
        // Show the loader icon
        this.set(event.keypath + '.submitting', true);
      },
      handleAbortCheckIn(event, checkin) {
        event.original.preventDefault();
        var participantID = this.get(event.keypath + '.pid');
        if(checkin) {
          this.get('checkinQ').dequeue(participantID)
          this.get('cancelcheckinQ').enqueue(participantID);
        } else {
          this.get('cancelcheckinQ').dequeue(participantID)
          this.get('checkinQ').enqueue(participantID);
        }
        // Hide the loader icon
        this.set(event.keypath + '.submitting', false);
      },
      updateList() {
        $.ajax({
          type: 'GET',
          url: participantlistUrl,
          timeout: 5000,
          dataType: 'json',
          success: function(data) {
            count.set({
              total_participants: data.total_participants,
              total_checkedin: data.total_checkedin
            });
            list.set('participants', data.participants).then(function() {
              let participants = Utils.tohashMap(data.participants, "pid");
              list.get('checkinQ').updateQueue(participants, list);
              list.get('cancelcheckinQ').updateQueue(participants, list);
            });
          }
        });
      },
      onrender() {
        this.updateList();

        /* Read 'checkin-queue' and 'cancelcheckin-queue' every 8 seconds 
        and batch post check-in/cancel check-in status to server */
        setInterval(function() { 
          ParticipantTable.processQueues(list); 
        }, 8000);

        // Get participants data from server every 15 seconds
        setInterval(function() { 
          list.updateList(); 
        }, 15000);
      }
    });
  },
  processQueues(list) {
    let participantIDs = list.get('checkinQ').readAll();
    if (participantIDs) {
      this.postCheckinStatus(participantIDs, true, list);
    }

    participantIDs = list.get('cancelcheckinQ').readAll();
    if (participantIDs) {
      this.postCheckinStatus(participantIDs, false, list);
    }
  },
  postCheckinStatus(participantIDs, action, list) {
    let participants, checkin = 'f', content, formValues;
    participants = $.param({
      'pid': participantIDs
    }, true);
    if (action) {
      checkin = 't';
    }
    content = $("meta[name='csrf-token']").attr('content');
    formValues = `${participants}&checkin=${checkin}&csrf_token=${content}`;
    $.ajax({
      type: 'POST',
      url:  list.get('checkinUrl'),
      data : formValues,
      timeout: 5000,
      dataType: 'json',
      success(data) {
        if (data.checked_in) {
          data.participant_ids.forEach((participantId) => {
            list.get('checkinQ').dequeue(participantId);
          });
        } else {
          data.participant_ids.forEach((participantId) => {
            list.get('cancelcheckinQ').dequeue(participantId);
          });
        }
      }
    });
  }
};

$(() => {
  window.HasGeek.EventInit = function ({checkin='', search=''}) {
    if (checkin) {
      ParticipantTable.init(checkin);
    }

    if (search) {
      let tableSearch = new TableSearch(search.tableId);
      let inputId = `#${search.inputId}`;
      let tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function() {
        $(tableRow).addClass('mui--hide');
        var hits = tableSearch.searchRows($(this).val());
        $(hits.join(",")).removeClass('mui--hide');
      });
    }
  };
});

