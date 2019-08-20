import Vue from 'vue/dist/vue.min';
import { Utils, SaveProject } from './util';

const Schedule = {
  renderScheduleTable() {
    const schedule = this;

    const scheduleUI = Vue.component('schedule', {
      template: schedule.config.scriptTemplate,
      data() {
        return {
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
            description: schedule.config.pageDescription,
          },
          view: 'agenda',
        };
      },
      methods: {
        toggleTab(room) {
          if (this.width < window.HasGeek.config.mobileBreakpoint) {
            this.activeTab = room;
          }
        },
        toggleView(event, view) {
          event.preventDefault();
          this.view = view;
        },
        getTimeStr(time) {
          return new Date(parseInt(time, 10)).toLocaleTimeString().replace(/(.*)\D\d+/, '$1');
        },
        getColumnWidth(columnType) {
          if (columnType === 'header' || this.width >= window.HasGeek.config.mobileBreakpoint) {
            if (this.view === 'calendar') {
              return (this.timeSlotWidth / this.rowWidth);
            }
          }
          return 0;
        },
        getColumnHeight(duration, rowHeight) {
          return duration * rowHeight;
        },
        hasActiveRoom(session) {
          return Object.prototype.hasOwnProperty.call(session.rooms[this.activeTab], 'talk');
        },
        removeImg(descriptionHtml) {
          return descriptionHtml.replace(/<img[^>]*>/g, '').substring(0, 400).concat('..');
        },
        updateMetaTags(pageDetails) {
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
          $('#session-modal').on($.modal.CLOSE, () => {
            this.modalHtml = '';
            window.history.pushState('', '', this.pageDetails.url);
            this.updateMetaTags(this.pageDetails);
          });
          // Event listener for back key press since opening modal update browser history
          $(window).on('popstate', () => {
            if (this.modalHtml) {
              $.modal.close();
            } else if (window.history.state) {
              // Open the modal with previous session viewed
              this.openModal(window.history.state.html,
                window.history.state.backPage, window.history.state.pageDetails);
            }
          });
        },
        openModal(sessionHtml, backPage, pageDetails) {
          this.modalHtml = sessionHtml;
          $('#session-modal').modal('show');
          window.history.pushState({
            html: sessionHtml, backpage: backPage, pageDetails,
          }, '', backPage);
          this.updateMetaTags(pageDetails);
        },
        showSessionModal(activeSession) {
          const backPage = `${this.pageDetails.url}/${activeSession.url_name_suuid}`;
          const pageDetails = {
            title: `${activeSession.title} — ${this.pageDetails.projectTitle}`,
            pageTitle: activeSession.title,
            description: activeSession.speaker ? `${activeSession.title} by ${activeSession.speaker}`
              : `${activeSession.title}, ${this.pageDetails.projectTitle}`,
            url: backPage,
          };
          if (activeSession.modal_url) {
            $.ajax({
              url: activeSession.modal_url,
              type: 'GET',
              success: (sessionHtml) => {
                this.openModal(sessionHtml, backPage, pageDetails);
              },
              error() {
                window.toastr.error('There was a problem in contacting the server. Please try again later.');
              },
            });
          }
        },
        disableScroll(event, id) {
          event.preventDefault();
          Utils.animateScrollTo($(`#${id}`).offset().top - this.headerHeight);
        },
        handleBrowserResize() {
          $(window).resize(() => {
            this.width = $(window).width();
            this.height = $(window).height();

            if (this.width < 768) {
              this.view = 'agenda';
            }
          });
        },
        animateWindowScrollWithHeader() {
          this.headerHeight = 2 * $('.schedule__row--sticky').height();
          this.pathName = window.location.pathname;
          const scrollPos = JSON.parse(window.sessionStorage.getItem('scrollPos'));
          const activeSession = schedule.config.active_session;
          if (activeSession) {
            // Open session modal
            const paths = window.location.href.split('/');
            paths.pop();
            this.pageDetails.url = paths.join('/');
            this.showSessionModal(activeSession);
            // Scroll page to session
            Utils.animateScrollTo($(`#${activeSession.url_name_suuid}`).offset().top - this.headerHeight);
          } else if (window.location.pathname === this.pathName && window.location.hash) {
            const hash = window.location.hash.indexOf('/') !== -1
              ? window.location.hash.substring(0, window.location.hash.indexOf('/')) : window.location.hash;
            Utils.animateScrollTo($(hash).offset().top - this.headerHeight);
          } else if (scrollPos && scrollPos.pageTitle === this.pageDetails.projectTitle) {
            // Scroll page to last viewed position
            Utils.animateScrollTo(scrollPos.scrollPosY);
          } else {
            // Scroll page to schedule table
            Utils.animateScrollTo($(schedule.config.parentContainer).offset().top);
          }

          // On exiting the page, save page scroll position in session storage
          $(window).bind('beforeunload', () => {
            const scrollDetails = {
              pageTitle: this.pageDetails.projectTitle,
              scrollPosY: window.scrollY,
            };
            window.sessionStorage.setItem('scrollPos', JSON.stringify(scrollDetails));
          });
        },
      },
      mounted() {
        this.animateWindowScrollWithHeader();
        this.handleBrowserResize();
        this.handleBrowserHistory();
      },
    });

    const scheduleApp = new Vue({
      components: {
        scheduleUI,
      },
    });
    scheduleApp.$mount(schedule.config.divElem);
  },
  addSessionToSlots() {
    this.config.sessions.forEach((session) => {
      if (!session.room_scoped_name) {
        [session.room_scoped_name] = Object.keys(this.config.rooms);
      }
      session.startTime = this.Utils.getTime(session.start_at);
      session.endTime = this.Utils.getTime(session.end_at);
      session.eventDay = this.Utils.getEventDay(session.start_at, this.config.eventDayhashes);
      session.duration = this.Utils.getDuration(session.end_at,
        session.start_at, this.config.slotInterval);
      if (this.config.schedule[session.eventDay]) {
        this.config.schedule[session.eventDay].sessions[session.startTime].showLabel = true;
        this.config.schedule[session.eventDay].sessions[session.startTime]
          .rooms[session.room_scoped_name].talk = session;
      }
    });
  },
  createSlots() {
    this.config.eventDayhashes = {
    };
    this.config.schedule.forEach((day, index) => {
      day.dateStr = this.Utils.getDateString(day.start_at);
      day.startTime = this.Utils.getTime(day.start_at);
      day.endTime = this.Utils.getTime(day.end_at);
      day.rooms = JSON.parse(JSON.stringify(this.config.rooms));
      this.config.eventDayhashes[this.Utils.getEventDate(day.date)] = index;
      const slots = {
      };
      let sessionSlots = day.startTime;
      let endSessionSlot;
      while (sessionSlots < day.endTime) {
        endSessionSlot = sessionSlots;
        slots[sessionSlots] = {
          showLabel: false, rooms: JSON.parse(JSON.stringify(this.config.rooms)),
        };
        sessionSlots = new Date(sessionSlots);
        sessionSlots = sessionSlots.setMinutes(sessionSlots.getMinutes()
          + this.config.slotInterval);
      }
      slots[endSessionSlot].showLabel = true;
      day.sessions = JSON.parse(JSON.stringify(slots));
    });
  },
  init(config) {
    this.config = config;
    this.config.rooms = {
    };
    this.config.venues.forEach((venue) => {
      venue.room_list.forEach((room) => {
        this.config.rooms[room.scoped_name] = room;
        this.config.rooms[room.scoped_name].venue_title = venue.title;
      });
    });
    this.Utils.setTimeZoneOffset(this.config.timezoneOffset);

    if (Object.keys(this.config.rooms).length) {
      this.createSlots();
      this.addSessionToSlots();
      this.renderScheduleTable();
    }
  },
  Utils: {
    setTimeZoneOffset(timezoneOffset) {
      // The time difference between UTC and project timezone in milliseconds
      this.timezoneOffset = timezoneOffset;
    },
    getTimeZoneOffset() {
      /* new Date().getTimezoneOffset() - the time difference
         between UTC and browser timezone in minutes
      */
      const jsDate = new Date();
      return (jsDate.getTimezoneOffset() * 60000 + this.timezoneOffset);
    },
    getEventDay(eventDate, eventDayshash) {
      const day = this.getEventDate(eventDate);
      return eventDayshash[day];
    },
    getEventDate(eventDate) {
      const date = new Date(this.getTime(eventDate));
      return date.getDate();
    },
    getTime(dateTime) {
      return new Date(new Date(dateTime).getTime() + this.getTimeZoneOffset()).getTime();
    },
    getDateString(eventDate) {
      return new Date(this.getTime(eventDate)).toDateString();
    },
    getDuration(endDate, startDate, slotInterval) {
      const duration = new Date(endDate) - new Date(startDate);
      // Convert to minutes and multiply by slotInterval
      return duration / 1000 / 60 / slotInterval;
    },
  },
};

$(() => {
  window.HasGeek.ScheduleInit = function initSchedule(config, saveProjectConfig) {
    Schedule.init(config);

    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }
  };
});
