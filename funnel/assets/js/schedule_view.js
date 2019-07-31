import { Utils, SaveProject } from './util';
import Ractive from "ractive";

const Schedule = {
  renderScheduleTable() {
    Ractive.DEBUG = false;
    let schedule = this;

    let scheduleUI = new Ractive({
      el: schedule.config.divElem,
      template: schedule.config.scriptTemplate,
      data: {
        schedules: schedule.config.schedule,
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
          if (columnType === 'header' || this.get('width') > 767 ) {
            if (this.get('view') === 'calendar') {
              return (this.get('timeSlotWidth')/this.get('rowWidth'));
            } else {
              return 0;
            }
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
  addSessionToSlots() {
    this.config.sessions.forEach((session) => {
      if(!session.room_scoped_name) {
        [session.room_scoped_name] = Object.keys(this.config.rooms);
      }
      session.startTime = this.Utils.getTime(session.start_at);
      session.endTime = this.Utils.getTime(session.end_at);
      session.eventDay = this.Utils.getEventDay(session.start_at, this.config.eventDayhashes);
      session.duration = this.Utils.getDuration(session.end_at, session.start_at, this.config.slotInterval);
      if(this.config.schedule[session.eventDay]) {
        this.config.schedule[session.eventDay]['sessions'][session.startTime].showLabel = true;
        this.config.schedule[session.eventDay]['sessions'][session.startTime]
          .rooms[session.room_scoped_name].talks = session;
      }
    });
  },
  createSlots() {
    this.config.eventDayhashes = {};
    this.config.schedule.forEach((day, index) => {
      day.dateStr = this.Utils.getDateString(day.date);
      day.startTime = this.Utils.getTime(day.start_at);
      day.endTime = this.Utils.getTime(day.end_at);
      day.rooms = JSON.parse(JSON.stringify(this.config.rooms));
      this.config.eventDayhashes[this.Utils.getEventDate(day.date)] = index;
      let slots = {};
      let sessionSlots = day.startTime;
      while(sessionSlots < day.endTime) {
        slots[sessionSlots] = {showLabel: false, rooms: JSON.parse(JSON.stringify(this.config.rooms))};
        sessionSlots = new Date(sessionSlots);
        sessionSlots = sessionSlots.setMinutes(sessionSlots.getMinutes() + this.config.slotInterval);
      };
      day.sessions = JSON.parse(JSON.stringify(slots));
    });
  },
  init(config) {
    var t0 = performance.now();
    var t1;

    this.config = config;
    this.config.rooms = {};
    this.config.venues.forEach((venue) => {
      venue.room_list.forEach((room) => {
        this.config.rooms[room.scoped_name] = room;
        this.config.rooms[room.scoped_name].venue_title = venue.title;
      });
    });
    t1 = performance.now();
    console.log("Call to add rooms to config took " + (t1 - t0) + " milliseconds.");

    t0 = performance.now();
    this.createSlots();
    t1 = performance.now();
    console.log("Call to createSlots took " + (t1 - t0) + " milliseconds.");

    t0 = performance.now();
    this.addSessionToSlots();
    t1 = performance.now();
    console.log("Call to addSessionToScheduleTb took " + (t1 - t0) + " milliseconds.");
    
    t0 = performance.now();
    this.renderScheduleTable();
    t1 = performance.now();
    console.log("Call to renderScheduleTable took " + (t1 - t0) + " milliseconds.");
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
  window.HasGeek.ScheduleInit = function (config, saveProjectConfig) {
    Schedule.init(config);

    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }
  };
});
