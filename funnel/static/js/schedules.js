var date_diff = function(from, to) {
    return (to.valueOf() - from.valueOf())/3600/24000;
};

var inactive_days_array = function(from, to) {
    var diff = date_diff(from, to);
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
                title: $.trim($(this).text()), // use the element's text as the event title
                saved: false,
                data: {
                    proposal_space_id: $(this).attr('data-proposal-space-id'),
                    proposal_id: $(this).attr('data-proposal-id')
                }
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
    var buttons = {};
    // Default config for calendar
    var config = {
        header: {
            left: '',
            center: 'title',
            right: ''
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
        copiedEventObject.end = new Date(date.getTime());
        copiedEventObject.end.setMinutes(copiedEventObject.end.getMinutes() + config.defaultEventMinutes);
        copiedEventObject.allDay = allDay;
        copiedEventObject.data.start = copiedEventObject.start.valueOf();
        copiedEventObject.data.end = copiedEventObject.end.valueOf();

        // render the event on the calendar
        // the last `true` argument determines if the event "sticks" (http://arshaw.com/fullcalendar/docs/event_rendering/renderEvent/)
        container.fullCalendar('renderEvent', copiedEventObject, true);

        $(this).remove();
        
        buttons.save.enable('Save');
    };
    config.eventClick = function(event, jsEvent, view) {
        // TODO: popup session edit form
    };

    var onEventChange = function(event, jsEvent, ui, view) {
        event.data.start = event.start.valueOf();
        event.end.start = event.end.valueOf();
        event.saved = false;
        buttons.save.enable('Save');
    };

    config.eventDragStop = config.eventResizeStop = onEventChange;

    var init_buttons = function() {
        container.find('.fc-header-right').append('<span class="hg-fc-button save-schedule">Save</span>');
        buttons.save = container.find('.save-schedule');
        container.find('.hg-fc-button').addClass(
            'fc-button fc-state-default fc-corner-left fc-corner-right'
            ).attr('unselectable', 'on');
        container.find('.hg-fc-button').hover(function(){
            $(this).addClass('fc-state-hover');
        }, function() {
            $(this).removeClass('fc-state-hover');
        });
        for(i in buttons) {
            buttons[i].enable = function(value) {
                $(this).removeClass('fc-state-disabled');
                if(typeof value != 'undefined') {
                    $(this).text(value);
                }
            };
            buttons[i].disable = function(value) {
                $(this).addClass('fc-state-disabled');
                if(typeof value != 'undefined') {
                    $(this).text(value);
                }
            };
            buttons[i].disabled = function() {
                $(this).hasClass('fc-state-disabled');
            };
        }
        buttons.save.disable('Saved');
        buttons.save.click(function() {
            if(!buttons.save.disabled()) {
                save_schedule();
            }
        });
    };

    var is_not_saved = function(event) {
        return !event.saved;
    };

    var save_schedule = function() {
        buttons.save.disable('Saving...');
        var events = container.fullCalendar('clientEvents', is_not_saved);
        for(i in events) {
            events[i].saved = true;
        }
        buttons.save.disable('Saved');
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

        // Show previous & next buttons only if the difference between start & end dates is more than a week
        if(date_diff(start, end) >= 7) config.header.left = 'prev,next today';

        container.fullCalendar(config);
        init_buttons();
    };

    return calendar;
}();
