import { Utils, SaveProject } from './util';
import Vue from 'vue/dist/vue.min';

const Schedule = {
  renderScheduleTable() {
    let schedule = this;

    let scheduleUI = Vue.component('schedule', {
      template: schedule.config.scriptTemplate,
      data: function () {
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
            description: schedule.config.pageDescription
          },
          view: 'agenda',
          activeSession: ''
        }
      },
      methods: {
        toggleTab(room) {
          if(this.width < 992) {
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
          if (columnType === 'header' || this.width > 767 ) {
            if (this.view === 'calendar') {
              return (this.timeSlotWidth/this.rowWidth);
            } else {
              return 0;
            }
          } else {
            return 0;
          }
        },
        getColumnHeight(duration, rowHeight) {
          return duration * rowHeight;
        },
        hasActiveRoom(session) {
          return Object.prototype.hasOwnProperty.call(session.rooms[this.activeTab], 'talk');
        },
        removeImg(descriptionHtml) {
          return descriptionHtml.replace(/<img[^>]*>/g,"").substring(0, 200).concat('..');
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
            this.modalHtml = '';
            window.history.pushState('', '', this.pageDetails['url']);
            this.updateMetaTags(this.pageDetails);
          });
          // Event listener for back key press since opening modal update browser history
          $(window).on('popstate', () => {
            if(this.modalHtml) {
              $.modal.close();
            } else if(window.history.state) {
              // Open the modal with previous session viewed
              this.openModal(window.history.state.html, window.history.state.backPage, window.history.state.pageDetails);
            }
          });
        },
        openModal: function(sessionHtml, backPage, pageDetails) {
          console.log('openModal', sessionHtml, backPage, pageDetails);
          this.modalHtml = sessionHtml;
          $("#session-modal").modal('show');
          window.history.pushState({html: sessionHtml, backpage: backPage, pageDetails: pageDetails}, '', backPage);
          this.updateMetaTags(pageDetails);
        },
        showSessionModal: function(activeSession) {
          let backPage, pageDetails;
          backPage = this.pageDetails['url'] + '/' + activeSession.url_name_suuid;
          pageDetails = {
            title: `${activeSession.title} — ${this.pageDetails['projectTitle']}`,
            pageTitle: activeSession.title,
            description: activeSession.speaker ? `${activeSession.title} by ${activeSession.speaker}` : `${activeSession.title}, ${this.pageDetails['projectTitle']}`,
            url: backPage
          };
          if(activeSession.modal_url) {
            $.ajax({
              url: activeSession.modal_url,
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
        disableScroll(event, id) {
          event.preventDefault();
          Utils.animateScrollTo($('#' + id).offset().top - this.headerHeight);
        },
        handleBrowserResize() {
          $(window).resize(() => {
            scheduleUI.width = $(window).width();
            scheduleUI.height = $(window).height();

            if(scheduleUI.width < 768) {
              scheduleUI.view = 'agenda';
            }
          });
        },
        animateWindowScrollWithHeader: function() {
          this.headerHeight =  2 * $('.schedule__row--sticky').height();
          this.pathName = window.location.pathname;
          let scrollPos = JSON.parse(window.sessionStorage.getItem('scrollPos'));
          
          let activeSession = schedule.config.active_session;
          if(activeSession) {
            // Open session modal
            var paths = window.location.href.split('/');
            paths.pop()
            this.pageDetails.url = paths.join('/');
            this.showSessionModal(activeSession);
            // Scroll page to session
            console.log($("#" + activeSession.url_name_suuid))
            Utils.animateScrollTo($("#" + activeSession.url_name_suuid).offset().top - this.headerHeight);
          } else if(window.location.pathname === this.pathName && window.location.hash) {
            let hash;
            hash = window.location.hash.indexOf('/') !== -1 ?
              window.location.hash.substring(0, window.location.hash.indexOf('/')) : window.location.hash;
            console.log('hash', hash);
            Utils.animateScrollTo($(hash).offset().top - this.headerHeight);
          } else if(scrollPos && scrollPos.pageTitle === this.pageDetails['projectTitle']) {
            // Scroll page to last viewed position
            console.log('scrollPosY', scrollPos.scrollPosY);
            Utils.animateScrollTo(scrollPos.scrollPosY);
          } else {
            // Scroll page to schedule table
            console.log('divElem', $(schedule.config.parentContainer));
            Utils.animateScrollTo($(schedule.config.parentContainer).offset().top);
          }

          // On exiting the page, save page scroll position in session storage
          window.onbeforeunload = function() {
            let scrollDetails = {
              'pageTitle': scheduleUI.pageDetails['projectTitle'],
              'scrollPosY': window.scrollY
            };
            window.sessionStorage.setItem('scrollPos', JSON.stringify(scrollDetails));
          };
        },
      },
      mounted() {
        this.animateWindowScrollWithHeader();
        this.handleBrowserResize();
        this.handleBrowserHistory();
      },
    });

    let scheduleApp = new Vue({
      components: {
        scheduleUI
      },
      render: function(createElement) {
        return createElement(scheduleUI);
      }
    });
    scheduleApp.$mount(schedule.config.divElem);
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
          .rooms[session.room_scoped_name].talk = session;
      }
    });
    console.log('addSessionToSchedule', JSON.parse(JSON.stringify(this.config.schedule)));
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

    if(Object.keys(this.config.rooms).length) {
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
    }

    return;
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
