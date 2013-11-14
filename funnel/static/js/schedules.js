var inactive_days_array = function(from, to) {
    var diff = (to.valueOf() - from.valueOf())/3600/24000;
    if(diff >= 7) return [];
    else {
        var from_day = from.getDay(), to_day = to.getDay();
        var inactive = [];
        for(i=0; i <= 6; i++) {
            if(i == from_day) i = to_day;
            else inactive.push(i);
        }
        return inactive;
    }
};

var proposals = function(){
    var container = $('#proposals');
    var init = function() {
        // Make proposals draggable
        container.find('.unscheduled').each(function(){
            // create an Event Object (http://arshaw.com/fullcalendar/docs/event_data/Event_Object/)
            // it doesn't need to have a start or end
            var eventObject = {
                title: $.trim($(this).text()) // use the element's text as the event title
            };
            // store the Event Object in the DOM element so we can get to it later
            $(this).data('eventObject', eventObject);
            // make the event draggable using jQuery UI
            $(this).draggable({
                zIndex: 999,
                revert: true,      // will cause the event to go back to its
                revertDuration: 0  //  original position after the drag
            });
        });
    }();
    return {};
}();

var calendar = function() {
    var calendar = {};
    var container = $('#calendar');
    var start, end, schedule_url;
    // Default config for calendar
    var config = {
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay'
        },
        allDayDefault: false,
        firstDay: 1, //Start from Monday, if not modified
        defaultView: 'agendaWeek',
        allDaySlot: false,
        slotMinutes: 15,
        defaultEventMinutes: 45,
        firstHour: 8,
        slotEventOverlap: false,
        columnFormat: {
            month: 'ddd',  // Mon
            week: 'ddd d', // Mon 31
            day: 'dddd d'  // Monday 31
        },
        selectable: true,
        editable: true,
        droppable: true,
        selectHelper: true, // TODO: Replace with function(start, end) returning DOM element
    };
    config.drop = function(date, allDay) {
        // retrieve the dropped element's stored Event Object
        var originalEventObject = $(this).data('eventObject');

        // we need to copy it, so that multiple events don't have a reference to the same object
        var copiedEventObject = $.extend({}, originalEventObject);

        // assign it the date that was reported
        copiedEventObject.start = date;
        copiedEventObject.allDay = allDay;

        // render the event on the calendar
        // the last `true` argument determines if the event "sticks" (http://arshaw.com/fullcalendar/docs/event_rendering/renderEvent/)
        container.fullCalendar('renderEvent', copiedEventObject, true);

        $(this).remove();
        // TODO: create session from proposal in the backend
    };
    config.eventClick = function(event, jsEvent, view) {
        // TODO: popup session edit form
    };
    calendar.init = function(url, from, to) {
        //Initialise data for calendar
        start = new Date(from);
        end = new Date(to);
        schedule_url = url;

        //Configure calendar if from & to dates are set.
        if(from != null && to != null) {
            config.hiddenDays = inactive_days_array(start, end);
            config.firstDay = start.getDay();
            config.year = start.getFullYear();
            config.month = start.getMonth();
            config.date = start.getDate();
        }
        container.fullCalendar(config);
    };

    return calendar;
}();
