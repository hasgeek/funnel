import {Utils} from './util';
import Ractive from "ractive";

const Schedule = {
  renderScheduleTable() {
    Ractive.DEBUG = false;
    let schedule = this;

    let scheduleUI = new Ractive({
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
        pageDetails: {
          url: window.location.href,
          title: `Schedule – ${schedule.config.projectTitle}`,
          projectTitle: schedule.config.projectTitle,
          pageTitle: 'Schedule',
          description: schedule.config.pageDescription
        },
        view: 'calendar',
        getTimeStr(time) {
          return new Date(parseInt(time, 10)).toLocaleTimeString().replace(/(.*)\D\d+/, '$1');
        },
        getColumnWidth(columnType) {
          if (columnType === 'header' || this.get('width') > 991) {
            return (this.get('timeSlotWidth')/this.get('rowWidth'));
          } else {
            return 0;
          }
        },
        hasActiveRoom(session) {
          return Object.prototype.hasOwnProperty.call(session.rooms[this.get('activeTab')], 'talks');
        },
        removeImg(descriptionHtml) {
          return descriptionHtml.replace(/<img[^>]*>/g,"");
        }
      },
      toggleTab(event, room) {
        if(this.get('width') < 992) {
          event.original.preventDefault();
          this.set('activeTab', room);
        }
      },
      toggleView(event, view) {
        event.original.preventDefault();
        this.set('view', view);
      },
      updateMetaTags: function(pageDetails) {
        $('title').html(pageDetails.title);
        $('meta[name="DC.title"]').attr('content', pageDetails.pageTitle);
        $('meta[property="og:title"]').attr('content', pageDetails.pageTitle);
        $('meta[name=description]').attr('content', pageDetails.description);
        $('meta[property="og:description"]').attr('content', pageDetails.description);
        $('link[rel=canonical]').attr('href', pageDetails.url);
        $('meta[property="og:url"]').attr('content', pageDetails.url);
      },
      handleBrowserHistory() {
        // On closing modal, update browser history
        $("#session-modal").on($.modal.CLOSE, () => {
          this.set('modalHtml', '');
          window.history.pushState('', '', this.get('pageDetails')['url']);
          this.updateMetaTags(this.get('pageDetails'));
        });
        // Event listener for back key press since opening modal update browser history
        $(window).on('popstate', () => {
          if(this.get('modalHtml')) {
            $.modal.close();
          } else if(window.history.state) {
            // Open the modal with previous session viewed
            this.openModal(window.history.state.html, window.history.state.backPage, window.history.state.pageDetails);
          }
        });
      },
      openModal: function(sessionHtml, backPage, pageDetails) {
        this.set('modalHtml', sessionHtml);
        $("#session-modal").modal('show');
        window.history.pushState({html: sessionHtml, backpage: backPage, pageDetails: pageDetails}, '', backPage);
        this.updateMetaTags(pageDetails);
      },
      showSessionModal: function(event, activeSession) {
        let sessionModalUrl, sessionUuid, backPage, pageDetails;
        sessionModalUrl = event ? this.get(event.keypath + '.talks.modal_url') : activeSession.modal_url;
        sessionUuid = event ? this.get(event.keypath + '.talks.url_name_suuid') : activeSession.url_name_suuid;
        backPage = this.get('pageDetails')['url'] + '/' + sessionUuid;
        if (event) {
          pageDetails = {
            title: this.get(event.keypath + '.talks.title') + ' — ' + this.get('pageDetails')['projectTitle'],
            pageTitle: this.get(event.keypath + '.talks.title'),
            description: this.get(event.keypath + '.talks.speaker') ? this.get(event.keypath + '.talks.title') + ' by ' + this.get(event.keypath + '.talks.speaker') : this.get(event.keypath + '.talks.title') + ", " + this.get('pageDetails')['projectTitle'],
            url: backPage
          };
        } else {
          pageDetails = {
            title: activeSession.title + ' – ' + this.get('pageDetails')['projectTitle'],
            pageTitle: activeSession.title,
            description: activeSession.speaker ? activeSession.title + ' by ' + activeSession.speaker : activeSession.title + ", " + this.get('pageDetails')['projectTitle'],
            url: backPage
          };
        }
        if(sessionModalUrl) {
          $.ajax({
            url: sessionModalUrl,
            type: 'GET',
            success: (sessionHtml) => {
              this.openModal(sessionHtml, backPage, pageDetails);
            },
            error() {
              window.toastr.error('There was a problem in contacting the server. Please try again later.');
            }
          });
        }
      },
      disableScroll(event) {
        event.original.preventDefault();
        window.location.hash = event.node.id;
        Utils.animateScrollTo($(window.location.hash).offset().top - this.get('headerHeight'));
      },
      handleBrowserResize() {
        $(window).resize(() => {
          scheduleUI.set('width', $(window).width());
          scheduleUI.set('height', $(window).height());
        });
      },
      animateWindowScrollWithHeader: function() {
        this.set('headerHeight', 2 * $('.schedule__row--sticky').height());
        this.set('pathName', window.location.pathname);
        let scrollPos = JSON.parse(window.sessionStorage.getItem('scrollPos'));
        
        let activeSession = schedule.config.active_session;
        if(activeSession) {
          // Open session modal
          var paths = window.location.href.split('/');
          paths.pop()
          this.set('pageDetails.url', paths.join('/'));
          this.showSessionModal('', activeSession);
          // Scroll page to session
          Utils.animateScrollTo($("#" + activeSession.url_name_suuid).offset().top - this.get('headerHeight'));
        } else if(window.location.pathname === this.get('pathName') && window.location.hash) {
          let hash;
          hash = window.location.hash.indexOf('/') !== -1 ?
            window.location.hash.substring(0, window.location.hash.indexOf('/')) : window.location.hash;
          Utils.animateScrollTo($(hash).offset().top - this.get('headerHeight'));
        } else if(scrollPos && scrollPos.pageTitle === this.get('pageDetails')['projectTitle']) {
          // Scroll page to last viewed position
          Utils.animateScrollTo(scrollPos.scrollPosY);
        } else {
          // Scroll page to schedule table
          Utils.animateScrollTo($(schedule.config.divElem).offset().top);
        }

        // On exiting the page, save page scroll position in session storage
        window.onbeforeunload = function() {
          let scrollDetails = {
            'pageTitle': scheduleUI.get('pageDetails')['projectTitle'],
            'scrollPosY': window.scrollY
          };
          window.sessionStorage.setItem('scrollPos', JSON.stringify(scrollDetails));
        };
      },
      oncomplete() {
        this.animateWindowScrollWithHeader();
        this.handleBrowserResize();
        this.handleBrowserHistory();
      }
    });
  },
  addSessionToSchedule() {
    this.config.scheduled.forEach((session) => {
      if(!session.room_scoped_name) {
        [session.room_scoped_name] = Object.keys(this.config.rooms);
      }
      if(this.config.scheduleTable[session.eventDay]) {
        this.config.scheduleTable[session.eventDay]['sessions'][session.startTime].showLabel = true;
        this.config.scheduleTable[session.eventDay]['sessions'][session.startTime]
          .rooms[session.room_scoped_name].talks = session;
      }
    });
  },
  createScheduleTable() {
    Object.keys(this.config.scheduleTable).forEach((eventDay) => {
      let slots = {};
      let sessionSlots = this.config.scheduleTable[eventDay].startTime;
      while(sessionSlots < this.config.scheduleTable[eventDay].endTime) {
        slots[sessionSlots] = {showLabel: false, rooms: JSON.parse(JSON.stringify(this.config.rooms))};
        sessionSlots = new Date(sessionSlots);
        sessionSlots = sessionSlots.setMinutes(sessionSlots.getMinutes() + this.config.slotInterval);
      };
      this.config.scheduleTable[eventDay].sessions = JSON.parse(JSON.stringify(slots));
    });
  },
  getEventDuration() {
    this.config.scheduled.forEach((session) => {
      session.startTime = this.Utils.getTime(session.start_at);
      session.endTime = this.Utils.getTime(session.end_at);
      session.eventDay = this.Utils.getEventDay(session.start_at, this.config.eventDayhash);
      session.duration = this.Utils.getDuration(session.end_at, session.start_at, this.config.slotInterval);
      if(this.config.scheduleTable[session.eventDay]) {
        this.config.scheduleTable[session.eventDay].startTime =
          this.config.scheduleTable[session.eventDay].startTime && this.config.scheduleTable[session.eventDay].startTime
          < new Date(session.start_at).getTime()
          ? this.config.scheduleTable[session.eventDay].startTime : new Date(session.start_at).getTime();
        this.config.scheduleTable[session.eventDay].endTime =
          this.config.scheduleTable[session.eventDay].endTime > new Date(session.end_at).getTime()
          ? this.config.scheduleTable[session.eventDay].endTime : new Date(session.end_at).getTime();
      }
    });
  },
  getEventDays() {
    let difference = (new Date(this.config.toDate) - new Date(this.config.fromDate))/ (1000 * 3600 * 24);
    this.config.eventDayhash = {};
    let eventDays = {}, seq = 0, nextDay = new Date(this.config.fromDate), day;
    while(seq <= difference) {
      day = nextDay.getDate();
      this.config.eventDayhash[day] = seq;
      eventDays[seq] = {dateStr: this.Utils.getDateString(nextDay), talks: {},
      startTime: 0, endTime: 0, rooms: JSON.parse(JSON.stringify(this.config.rooms))};
      seq += 1;
      nextDay.setDate(nextDay.getDate() + 1);
    };
    // To create a copy and not a reference
    this.config.scheduleTable = JSON.parse(JSON.stringify(eventDays));
    return;
  },
  init(config) {
    this.config = config;
    this.config.rooms = {};
    this.config.venues.forEach((venue) => {
      venue.room_list.forEach((room) => {
        this.config.rooms[room.scoped_name] = room;
        this.config.rooms[room.scoped_name].venue_title = venue.title;
      });
    });
    this.getEventDays();
    this.getEventDuration();
    this.createScheduleTable();
    this.addSessionToSchedule();
    this.renderScheduleTable();
  },
  Utils: {
    getEventDay(eventDate, eventDayshash) {
      let day = this.getEventDate(eventDate);
      return eventDayshash[day];
    },
    getEventDate(eventDate) {
      let date =  new Date(eventDate);
      return date.getDate();
    },
    getTime(dateTime) {
      return new Date(dateTime).getTime()
    },
    getDateString(eventDate) {
      return new Date(eventDate).toDateString();
    },
    getDuration(endDate, startDate, slotInterval) {
      let duration = new Date(endDate) - new Date(startDate);
      // Convert to minutes and multiply by slotInterval
      return duration/1000/60/slotInterval;
    },
  },
};

$(() => {
  window.HasGeek.ScheduleInit = function (config) {
    Schedule.init(config);
  };
});
