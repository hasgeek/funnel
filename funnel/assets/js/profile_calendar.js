import Vue from 'vue/dist/vue.min';
import FullCalendar from '@fullcalendar/vue';
import dayGridPlugin from '@fullcalendar/daygrid';
import multiMonthPlugin from '@fullcalendar/multimonth';
import { faSvg } from './utils/vue_util';

$(() => {
  /* eslint-disable no-new */
  const calendarApp = new Vue({
    el: '#calendar',
    components: {
      FullCalendar,
      faSvg,
    },
    data() {
      return {
        date: '',
        showFilter: false,
        calendarView: 'monthly',
        access: 'both',
        cfp: '',
        events: [],
        calendarOptions: {
          plugins: [dayGridPlugin, multiMonthPlugin],
          initialView: 'dayGridMonth',
          aspectRatio: 1.5,
          headerToolbar: {
            start: 'title',
            center: '',
            end: '',
          },
          showNonCurrentDates: false,
          dayMaxEventRows: 1,
          events: async function fetcEvents(info) {
            const url = `${window.location.href}?${new URLSearchParams({
              start: info.startStr,
              end: info.endStr,
            }).toString()}`;
            const response = await fetch(url, {
              headers: {
                Accept: 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
              },
            });
            if (response && response.ok) {
              const responseData = await response.json();
              calendarApp.events = responseData;
              return responseData;
            }
            return false;
          },
          eventTimeFormat: {
            // like '14:30:00'
            hour: '2-digit',
            minute: '2-digit',
            meridiem: 'short',
          },
        },
      };
    },
    mounted() {
      this.calendar = this.$refs.fullCalendar.getApi();
      this.updateTitle();
    },
    methods: {
      updateTitle() {
        this.date = this.calendar.currentData.viewTitle;
      },
      updateEvents() {
        this.events = this.calendar.getEvents();
      },
      prev() {
        this.calendar.prev();
        this.updateTitle();
      },
      next() {
        this.calendar.next();
        this.updateTitle();
      },
      toggleFilterMenu() {
        this.showFilter = !this.showFilter;
      },
      applyFilter() {
        this.showFilter = false; // Close filter menu
        switch (this.calendarView) {
          case 'monthly':
            this.calendar.changeView('dayGridMonth');
            break;
          case 'yearly':
            this.calendar.changeView('multiMonthYear');
            break;
          default:
            this.calendar.changeView('dayGridMonth');
        }
        this.updateTitle();
        this.updateEvents();
      },
      propertyVal(event, key) {
        return (
          event && (event[key] || (event.extendedProps && event.extendedProps[key]))
        );
      },
    },
    computed: {
      filteredEvents() {
        return this.events
          .filter((event) => {
            if (this.access === 'member') return event.member_access;
            if (this.access === 'free') return !event.member_access;
            return event;
          })
          .filter((event) => {
            if (this.cfp) return event.cfp_open === this.cfp;
            return event;
          });
      },
    },
  });
});
