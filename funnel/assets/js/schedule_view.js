import Vue from 'vue/dist/vue.min';
import toastr from 'toastr';
import { MOBILE_BREAKPOINT } from './constants';
import ScrollHelper from './utils/scrollhelper';
import { faSvg } from './utils/vue_util';
import Form from './utils/formhelper';
import Spa from './utils/spahelper';
import WebShare from './utils/webshare';
import initEmbed from './utils/initembed';
import Modal from './utils/modalhelper';

const Schedule = {
  renderScheduleTable() {
    const self = this;

    const scheduleUI = Vue.component('schedule', {
      template: self.config.scriptTemplate,
      data() {
        return {
          schedules: self.config.schedule,
          rowWidth: Object.keys(self.config.rooms).length,
          rowHeight: '30',
          timeSlotWidth: '75',
          timeZone: self.config.timeZone,
          rowBorder: '1',
          activeTab: Object.keys(self.config.rooms)[0],
          width: $(window).width(),
          height: $(window).height(),
          modalHtml: '',
          headerHeight: '',
          pageDetails: {
            url: window.location.href,
            title: `Schedule – ${self.config.projectTitle}`,
            projectTitle: self.config.projectTitle,
            pageTitle: 'Schedule',
            description: self.config.pageDescription,
          },
          view: 'agenda',
          svgIconUrl: window.Hasgeek.Config.svgIconUrl,
        };
      },
      methods: {
        toggleTab(room) {
          if (this.width < MOBILE_BREAKPOINT) {
            this.activeTab = room;
          }
        },
        toggleView(event, view) {
          event.preventDefault();
          this.view = view;
        },
        getTimeStr(time) {
          const options = {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: this.timeZone,
          };
          return new Date(parseInt(time, 10)).toLocaleTimeString('en-GB', options);
        },
        getColumnWidth(columnType) {
          if (columnType === 'header' || this.width >= MOBILE_BREAKPOINT) {
            if (this.view === 'calendar') {
              return this.timeSlotWidth / this.rowWidth;
            }
          }
          return 0;
        },
        getColumnHeight(duration, rowHeight) {
          return duration * rowHeight;
        },
        hasActiveRoom(session) {
          return Object.prototype.hasOwnProperty.call(
            session.rooms[this.activeTab],
            'talk',
          );
        },
        removeImg(descriptionHtml) {
          return descriptionHtml
            .replace(/<img[^>]*>/g, '')
            .substring(0, 400)
            .concat('..');
        },
        handleBrowserHistory() {
          // On closing modal, update browser history
          $('#session-modal').on($.modal.CLOSE, () => {
            this.modalHtml = '';
            if (self.config.replaceHistoryToModalUrl) {
              Spa.updateMetaTags(this.pageDetails);
              if (window.history.state.openModal) {
                window.history.back();
              }
            }
          });
          if (self.config.changeToModalUrl) {
            $(window).on('popstate', () => {
              if (this.modalHtml) {
                $.modal.close();
              }
            });
          }
        },
        openModal(sessionHtml, currentPage, pageDetails) {
          this.modalHtml = sessionHtml;
          $('#session-modal').modal('show');
          this.handleModalShown();
          if (self.config.replaceHistoryToModalUrl) {
            window.history.pushState(
              {
                openModal: true,
              },
              '',
              currentPage,
            );
            Spa.updateMetaTags(pageDetails);
          }
        },
        handleFetchError(error) {
          const errorMsg = Form.getFetchError(error);
          toastr.error(errorMsg);
        },
        async showSessionModal(activeSession) {
          const currentPage = `${this.pageDetails.url}/${activeSession.url_name_uuid_b58}`;
          const pageDetails = {
            title: `${activeSession.title} — ${this.pageDetails.projectTitle}`,
            pageTitle: activeSession.title,
            description: activeSession.speaker
              ? `${activeSession.title} by ${activeSession.speaker}`
              : `${activeSession.title}, ${this.pageDetails.projectTitle}`,
            url: currentPage,
          };
          if (activeSession.modal_url) {
            const response = await fetch(activeSession.modal_url, {
              headers: {
                Accept: 'text/x.fragment+html',
                'X-Requested-With': 'XMLHttpRequest',
              },
            }).catch(() => {
              toastr.error(window.Hasgeek.Config.errorMsg.networkError);
            });
            if (response && response.ok) {
              const responseData = await response.text();
              this.openModal(responseData, currentPage, pageDetails);
            } else {
              this.handleFetchError(response);
            }
          }
        },
        handleModalShown() {
          const targetNode = document.getElementById('session-modal');
          const config = { attributes: true, childList: true, subtree: true };
          const callback = (mutationList, observer) => {
            mutationList.forEach((mutation) => {
              if (mutation.type === 'childList') {
                Modal.activateZoomPopup();
                WebShare.enableWebShare();
                initEmbed(`#session-modal .markdown`);
                observer.disconnect();
              }
            });
          };
          const observer = new MutationObserver(callback);
          observer.observe(targetNode, config);
        },
        disableScroll(event, id) {
          event.preventDefault();
          ScrollHelper.animateScrollTo($(`#${id}`).offset().top - this.headerHeight);
        },
        getHeight() {
          this.headerHeight =
            ScrollHelper.getPageHeaderHeight() + $('.schedule__row--sticky').height();
        },
        handleBrowserResize() {
          $(window).resize(() => {
            this.width = $(window).width();
            this.height = $(window).height();

            if (this.width < MOBILE_BREAKPOINT) {
              this.view = 'agenda';
            }
            this.getHeight();
          });
        },
        animateWindowScrollWithHeader() {
          this.getHeight();
          this.pathName = window.location.pathname;
          const scrollPos = JSON.parse(window.sessionStorage.getItem('scrollPos'));
          const activeSession = self.config.active_session;
          if (activeSession) {
            // Open session modal
            const paths = window.location.href.split('/');
            paths.pop();
            this.pageDetails.url = paths.join('/');
            this.showSessionModal(activeSession);
            // Scroll page to session
            ScrollHelper.animateScrollTo(
              $(`#${activeSession.url_name_uuid_b58}`).offset().top - this.headerHeight,
            );
          } else if (
            window.location.pathname === this.pathName &&
            window.location.hash
          ) {
            const hash =
              window.location.hash.indexOf('/') !== -1
                ? window.location.hash.substring(0, window.location.hash.indexOf('/'))
                : window.location.hash;
            ScrollHelper.animateScrollTo($(hash).offset().top - this.headerHeight);
          } else if (
            scrollPos &&
            scrollPos.pageTitle === this.pageDetails.projectTitle
          ) {
            // Scroll page to last viewed position
            ScrollHelper.animateScrollTo(scrollPos.scrollPosY);
          } else if ($('.schedule__date--upcoming').length) {
            // Scroll to the upcoming schedule
            ScrollHelper.animateScrollTo(
              $('.schedule__date--upcoming').first().offset().top - this.headerHeight,
            );
          } else {
            // Scroll to the last schedule
            ScrollHelper.animateScrollTo(
              $('.schedule__date').last().offset().top - this.headerHeight,
            );
          }
          window.history.replaceState(
            {
              subPage: true,
              prevUrl: this.pageDetails.url,
              navId: window.history.state.navId,
              refresh: false,
            },
            '',
            this.pageDetails.url,
          );

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
        if (self.config.rememberScrollPos) {
          this.animateWindowScrollWithHeader();
        }
        this.handleBrowserResize();
        this.handleBrowserHistory();
      },
    });

    const scheduleApp = new Vue({
      components: {
        scheduleUI,
        faSvg,
      },
    });
    scheduleApp.$mount(self.config.divElem);
  },
  addSessionToSlots() {
    this.config.sessions.forEach((session) => {
      if (!session.room_scoped_name) {
        [session.room_scoped_name] = Object.keys(this.config.rooms);
      }
      session.startTime = this.Utils.getTime(session.start_at);
      session.endTime = this.Utils.getTime(session.end_at);
      session.eventDay = this.Utils.getEventDay(
        session.start_at,
        this.config.eventDayhashes,
      );
      session.duration = this.Utils.getDuration(
        session.end_at,
        session.start_at,
        this.config.slotInterval,
      );
      if (this.config.schedule[session.eventDay]) {
        this.config.schedule[session.eventDay].sessions[session.startTime].showLabel =
          true;
        this.config.schedule[session.eventDay].sessions[session.startTime].rooms[
          session.room_scoped_name
        ].talk = session;
      }
    });
  },
  createSlots() {
    this.config.eventDayhashes = {};
    this.config.schedule.forEach((day, index) => {
      day.dateStr = this.Utils.getDateString(day.start_at);
      day.upcoming = new Date(day.dateStr) >= new Date(this.config.currentDate);
      day.startTime = this.Utils.getTime(day.start_at);
      day.endTime = this.Utils.getTime(day.end_at);
      day.rooms = JSON.parse(JSON.stringify(this.config.rooms));
      this.config.eventDayhashes[this.Utils.getEventDate(day.start_at)] = index;
      const slots = {};
      let sessionSlots = day.startTime;
      while (sessionSlots <= day.endTime) {
        slots[sessionSlots] = {
          showLabel: false,
          rooms: JSON.parse(JSON.stringify(this.config.rooms)),
        };
        sessionSlots = new Date(sessionSlots);
        sessionSlots = sessionSlots.setMinutes(
          sessionSlots.getMinutes() + this.config.slotInterval,
        );
      }
      slots[day.endTime].showLabel = true;
      day.sessions = JSON.parse(JSON.stringify(slots));
    });
  },
  addDefaultRoom(venue) {
    this.config.rooms[venue.name] = {
      title: '',
      venue_title: '',
    };
  },
  init(config) {
    this.config = config;
    this.config.rooms = {};
    if (!this.config.venues.length) {
      // Add default Venue
      this.config.venues = [{ title: 'Schedule', name: 'Schedule', rooms: [] }];
    }
    this.config.venues.forEach((venue) => {
      if (venue.rooms.length) {
        venue.rooms.forEach((room) => {
          this.config.rooms[room.scoped_name] = room;
          this.config.rooms[room.scoped_name].venue_title = venue.title;
        });
      } else {
        this.addDefaultRoom(venue);
      }
    });
    this.config.currentDate = this.Utils.getDateString(new Date());

    this.Utils.setTimeZone(this.config.timeZone);

    this.createSlots();
    this.addSessionToSlots();
    this.renderScheduleTable();
  },
  Utils: {
    setTimeZone(timeZone) {
      this.timeZone = timeZone;
    },
    getEventDay(eventDate, eventDayshash) {
      const day = this.getEventDate(eventDate);
      return eventDayshash[day];
    },
    getEventDate(eventDate) {
      const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: this.timeZone,
      };
      // British English(en-GB) uses day-month-year order
      return new Date(eventDate).toLocaleDateString('en-GB', options);
    },
    getTime(dateTime) {
      return new Date(dateTime).getTime();
    },
    getDateString(eventDate) {
      const options = {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: this.timeZone,
      };
      // British English(en-GB) uses day-month-year order
      return new Date(eventDate).toLocaleDateString('en-GB', options);
    },
    getDuration(endDate, startDate, slotInterval) {
      const duration = new Date(endDate) - new Date(startDate);
      // Convert to minutes and multiply by slotInterval
      return duration / 1000 / 60 / slotInterval;
    },
  },
};

$(() => {
  window.Hasgeek.ScheduleInit = (config) => {
    Schedule.init(config);
  };
});
