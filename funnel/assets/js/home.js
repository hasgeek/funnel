import Mustache from "mustache";

const CalendarWidget = {
  init(calendarSelector) {
    const Widget = this;

    $(calendarSelector).each(function() {
      let startDate = $(this).data('date');
      let endDate = $(this).data('dateupto');
      let projectMonth = new Intl.DateTimeFormat('default', { month: 'short'}).format(new Date(startDate));
      let weekdays = Widget.getWeek();
      Widget.getDateArray(startDate, endDate, weekdays);
      let calendarTemplate = $(this).find('.calendar-template').html();
      $(this).html(Mustache.to_html(calendarTemplate, {'weekdays': weekdays, 'month': projectMonth}));
    });
  },
  getWeek() {
    // January 7, 2019 is a Monday
    let startDay = new Date('January 7, 2019');
    let weekdays = [];
    do {
      weekdays.push({
        'weekdayNarrow': new Intl.DateTimeFormat('default', { weekday: 'narrow'}).format(startDay),
        'weekdayProject': [],
      });
      startDay.setDate(startDay.getDate() + 1);
    } while(weekdays.length < 7);
    return weekdays;
  },
  getDay(date) {
    // calendar UI starts from Monday but new Date().getDay returns Sunday as 0
    return date.getDay() === 0 ? 6 : date.getDay() - 1;
  },
  getDateArray(startDate, endDate, weekdays) {
    let day = new Date(startDate);
    let dayCount = this.getDay(day);

    // Complete the beginning week
    if(dayCount !== 0) {
      do {
        day.setDate(day.getDate() - 1);
        dayCount = this.getDay(day);
        weekdays[dayCount]['weekdayProject'].push({date: day.getDate(), jsDate: day});
      } while (dayCount > 0);
      day = new Date(startDate);
    }

    while (day <= new Date(endDate)) {
      dayCount = this.getDay(day);
      weekdays[dayCount]['weekdayProject'].push({date: day.getDate(), jsDate: day, active: true});
      day.setDate(day.getDate() + 1);
    }

    // Complete the ending week
    if(dayCount !== 6) {
      day = new Date(endDate)
      do {
        day.setDate(day.getDate() + 1);
        dayCount = this.getDay(day);
        weekdays[dayCount]['weekdayProject'].push({date: day.getDate(), jsDate: day});
      } while (dayCount !== 6);
    };
  }
}

$(() => {
  window.HasGeek.HomeInit = function ({calendarSelector}) {
    CalendarWidget.init(calendarSelector);
  };
});

