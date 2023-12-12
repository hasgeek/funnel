import Utils from './utils/helper';
import TableSearch from './utils/tablesearch';
import { RactiveApp } from './utils/ractive_util';

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

class Queue {
  constructor(queueName) {
    this.queueName = queueName;

    // Adds a ticketParticipantId to queue
    this.enqueue = function enqueue(ticketParticipantId) {
      const ticketParticipantList = Store.read(this.queueName) || [];
      if (ticketParticipantList.indexOf(ticketParticipantId) === -1) {
        ticketParticipantList.push(ticketParticipantId);
        return Store.add(this.queueName, ticketParticipantList);
      }
      return false;
    };

    // Reads and returns all items from queue
    // Returns undefined when queue is empty or not defined
    this.readAll = function readAll() {
      const ticketParticipantList = Store.read(this.queueName);
      if (ticketParticipantList && ticketParticipantList.length) {
        return ticketParticipantList;
      }
      return false;
    };

    // Removes item from queue and returns true
    // Returns undefined when item not present in queue
    this.dequeue = function dequeue(ticketParticipantId) {
      const ticketParticipantList = Store.read(this.queueName);
      const index = ticketParticipantList
        ? ticketParticipantList.indexOf(ticketParticipantId)
        : -1;
      if (index !== -1) {
        // Remove item from queue and add updated queue to localStorage
        ticketParticipantList.splice(index, 1);
        Store.add(this.queueName, ticketParticipantList);
        return ticketParticipantId;
      }
      return false;
    };

    /* updateQueue: If participant in "checkin-queue" has already been checked-in
    then it is removed from checkin queue */
    this.updateQueue = function updateQueue(
      participantsHashMap,
      ticketParticipantList
    ) {
      const queue = this;
      const ticketParticipantIds = queue.readAll();
      const ticketParticipants = ticketParticipantList.get('ticket_participants');
      if (ticketParticipantIds) {
        ticketParticipantIds.forEach((ticketParticipantId) => {
          if (queue.queueName.indexOf('cancelcheckin-queue') > -1) {
            if (!participantsHashMap[ticketParticipantId].checked_in) {
              /* Participant's check-in has already been cancelled so remove
              from 'cancelcheckin-queue' */
              queue.dequeue(ticketParticipantId);
            } else {
              const index = Utils.findLoopIndex(
                ticketParticipants,
                'puuid_b58',
                ticketParticipantId
              );
              ticketParticipantList.set(
                `ticket_participants.${index}.submitting`,
                true
              );
            }
          } else if (participantsHashMap[ticketParticipantId].checked_in) {
            // Participant has been checked-in so remove from 'checkin-queue'
            queue.dequeue(ticketParticipantId);
          } else {
            const index = Utils.findLoopIndex(
              ticketParticipants,
              'puuid_b58',
              ticketParticipantId
            );
            ticketParticipantList.set(`ticket_participants.${index}.submitting`, true);
          }
        });
      }
    };
  }
}

const ParticipantTable = {
  init({ IsPromoter, isUsher, checkinUrl, participantlistUrl, ticketEventName }) {
    const count = new RactiveApp({
      el: '#ticket-participants-count',
      template: '#ticket-participants-count-template',
      data: {
        total_participants: '',
        total_checkedin: '',
      },
    });

    const list = new RactiveApp({
      el: '#ticket-participants-table-content',
      template: '#ticket-participant-row',
      data: {
        ticket_participants: '',
        checkinUrl,
        checkinQ: new Queue(`${ticketEventName}-checkin-queue`),
        cancelcheckinQ: new Queue(`${ticketEventName}-cancelcheckin-queue`),
        IsPromoter,
        isUsher,
        getCsrfToken() {
          return $('meta[name="csrf-token"]').attr('content');
        },
        getCheckinUrl() {
          return checkinUrl;
        },
      },
      handleCheckIn(event, checkin) {
        event.original.preventDefault();
        const ticketParticipantId = this.get(`${event.keypath}.puuid_b58`);
        if (checkin) {
          // Add participant id to checkin queue
          this.get('checkinQ').enqueue(ticketParticipantId);
        } else {
          this.get('cancelcheckinQ').enqueue(ticketParticipantId);
        }
        // Show the loader icon
        this.set(`${event.keypath}.submitting`, true);
      },
      handleAbortCheckIn(event, checkin) {
        event.original.preventDefault();
        const ticketParticipantId = this.get(`${event.keypath}.puuid_b58`);
        if (checkin) {
          this.get('checkinQ').dequeue(ticketParticipantId);
          this.get('cancelcheckinQ').enqueue(ticketParticipantId);
        } else {
          this.get('cancelcheckinQ').dequeue(ticketParticipantId);
          this.get('checkinQ').enqueue(ticketParticipantId);
        }
        // Hide the loader icon
        this.set(`${event.keypath}.submitting`, false);
      },
      async updateList() {
        const response = await fetch(participantlistUrl, {
          headers: {
            Accept: 'application/json',
          },
        });
        if (response && response.ok) {
          const data = await response.json();
          count.set({
            total_participants: data.total_participants,
            total_checkedin: data.total_checkedin,
          });
          list.set('ticket_participants', data.ticket_participants).then(() => {
            const ticketParticipants = Utils.tohashMap(
              data.ticket_participants,
              'puuid_b58'
            );
            list.get('checkinQ').updateQueue(ticketParticipants, list);
            list.get('cancelcheckinQ').updateQueue(ticketParticipants, list);
          });
        }
      },
      onrender() {
        this.updateList();

        /* Read 'checkin-queue' and 'cancelcheckin-queue' every 8 seconds
        and batch post check-in/cancel check-in status to server */
        setInterval(() => {
          ParticipantTable.processQueues(list);
        }, 8000);

        // Get ticket participants data from server every 15 seconds
        setInterval(() => {
          list.updateList();
        }, 15000);
      },
    });
  },
  processQueues(list) {
    let ticketParticipantIds = list.get('checkinQ').readAll();
    if (ticketParticipantIds) {
      this.postCheckinStatus(ticketParticipantIds, true, list);
    }

    ticketParticipantIds = list.get('cancelcheckinQ').readAll();
    if (ticketParticipantIds) {
      this.postCheckinStatus(ticketParticipantIds, false, list);
    }
  },
  async postCheckinStatus(ticketParticipantIds, action, list) {
    let checkin = 'f';

    let ticketParticipants = '';
    ticketParticipantIds.forEach((participantId) => {
      const param = new URLSearchParams({
        puuid_b58: participantId,
      });
      ticketParticipants = ticketParticipants
        ? `${ticketParticipants}&${param}`
        : param;
    });
    if (action) {
      checkin = 't';
    }
    const csrfToken = $("meta[name='csrf-token']").attr('content');

    const response = await fetch(list.get('checkinUrl'), {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `${ticketParticipants}&${new URLSearchParams({
        checkin,
        csrf_token: csrfToken,
      }).toString()}`,
    });
    if (response && response.ok) {
      const data = await response.json();
      if (data) {
        if (data.checked_in) {
          data.ticket_participant_ids.forEach((ticketParticipantId) => {
            list.get('checkinQ').dequeue(ticketParticipantId);
          });
        } else {
          data.ticket_participant_ids.forEach((ticketParticipantId) => {
            list.get('cancelcheckinQ').dequeue(ticketParticipantId);
          });
        }
      }
    }
  },
};

$(() => {
  window.Hasgeek.ticketEventInit = ({ checkin = '', search = '' }) => {
    if (checkin) {
      ParticipantTable.init(checkin);
    }

    if (search) {
      const tableSearch = new TableSearch(search.tableId);
      const inputId = `#${search.inputId}`;
      const tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function doTableSearch() {
        $(tableRow).addClass('mui--hide');
        const hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }
  };
});
