$(function() {
    var popup = function() {
        var obj = {};
        var popup = {
            container: $('#popup'),
            event: null,
            title: function() {return this.container.find('.modal-title')},
            body: function() {return this.container.find('.modal-body')},
            form: function(input) {
                if(typeof input == 'undefined') return this.container.find('form');
                else return this.form().find('[name=' + input + ']');
            },
            options: {
                backdrop: 'static',
                keyboard: false
            },
            pop: function() {
                this.container.modal(this.options);
            },
            hide: function() {popup.container.modal('hide');},
            save: function() {
                popup.form('start').val(popup.event.obj_data.start);
                popup.form('end').val(popup.event.obj_data.end);
                var data = popup.form().serializeArray();
                $.ajax({
                    url: popup.event.form_url,
                    type: 'POST',
                    data: data,
                    success: function(result) {
                        if(result.status) {
                            popup.event.obj_data.id = result.session_id;
                            popup.event.obj_data.title = result.title;
                            popup.event.form_url = result.form_url;
                            popup.event.saved = true;
                            popup.hide();
                        }
                        else {
                            popup.body().html(result.form);
                        }
                    }
                });
            }
        };

        obj.open = function(event) {
            popup.event = event;
            $.get(event.form_url, event.form_data, function(result) {
                popup.body().html(result);
            });
            popup.title().text(event.title);
            popup.body().html('Loading...');
            popup.pop();
        };

        obj.init = function() {
            popup.container.find('.save').click(popup.save);
        };

        return obj;
    }();

    var calendar = function() {
        var onEventChange = function(event, jsEvent, ui, view) {
            event.saved = false;
            calendar.helpers.add_obj_data(event);
        };
        var calendar = {
            container: $('#calendar'),
            helpers: {
                date_diff: function(from, to) {return (to.valueOf() - from.valueOf())/3600/24000;},
                inactive_days: function(from, to) {
                    var diff = calendar.helpers.date_diff(from,to);
                    if(diff >= 7) return [];
                    else {
                        var from_day = from.getDay(), to_day = to.getDay();
                        var inactive = [];
                        for(i=0; i <= 6; i++) {if(i == from_day) i = to_day;else inactive.push(i);}
                        return inactive;
                    }
                },
                add_obj_data: function(event) {
                    obj_data = $.extend({}, this.init_obj);
                    obj_data = $.extend(obj_data, event);
                    obj_data.end = obj_data.end.valueOf();
                    obj_data.start = obj_data.start.valueOf();
                    event.obj_data = obj_data;
                }
            },
            options: {
                config: {
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
                    drop: function(date, allDay) {
                        // we need to clone it, else we will lose it when we remove the source's DOM element
                        var source = $(this);
                        var _event = source.data('info');
                        var event = $.extend({}, _event);
                        // assign it the date that was reported
                        event.start = date;
                        event.end = new Date(date.getTime());
                        event.end.setMinutes(event.end.getMinutes() + calendar.options.config.defaultEventMinutes);
                        source.remove();
                        calendar.add(event);
                        popup.open(event);
                    },
                    eventClick: function(event, jsEvent, view) {popup.open(event);},
                    eventDragStop: onEventChange,
                    eventResizeStop: onEventChange
                }
            },
            init_weekdays: function() {
                if(from_date != null) {
                    this.options.config.year = from_date.getFullYear();
                    this.options.config.month = from_date.getMonth();
                    this.options.config.date = from_date.getDate();
                    if(to_date != null) {
                        this.options.config.hiddenDays = this.helpers.inactive_days(from_date, to_date);
                        this.options.config.firstDay = from_date.getDay();
                    }
                }
            },
            init_obj: {id: null, start: null, end: null, title: null},
            add: function(event) {
                this.helpers.add_obj_data(event);
                this.container.fullCalendar('renderEvent', event, true);
            },
            init: function() {
                this.init_weekdays();
                this.container.fullCalendar(this.options.config);
            }
        };
        var obj = {};
        var buttons = {};

        obj.init = function(events) {
            from_date = new Date(from_date);
            to_date = new Date(to_date);
            for(e in events) {
                events[e].start = new Date(events[e].start);
                events[e].end = new Date(events[e].end);
                calendar.helpers.add_obj_data(events[e])
            }
            calendar.options.config.events = events;
            calendar.init();
            popup.init();
        };

        return obj;

    }();
    var events = function() {
        var unscheduled_events = {
            container: $('#proposals .list'),
            add: function(element) {
                element.draggable(this.options.draggable);
                element.data('info', {
                    saved: false,
                    scheduled: false,
                    form_url: element.attr('data-form-url'),
                    title: $.trim(element.text())
                });
            },
            options: {
                draggable: {
                    zIndex: 999,
                    revert: true,
                    revertDuration: 0
                }
            }
        };
        unscheduled_events.container.find('.unscheduled').each(function() {
            unscheduled_events.add($(this));
        });

        calendar.init(scheduled);
        // var scheduled_events = 
    }();
});

var calendar = function() {
    var calendar = {};
    var container = $('#calendar');
    var start, end, urls;
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
        var event = $.extend({}, originalEventObject);

        // assign it the date that was reported
        event.start = date;
        event.end = new Date(date.getTime());
        event.end.setMinutes(event.end.getMinutes() + config.defaultEventMinutes);
        event.allDay = allDay;
        event.data.start = event.start.valueOf();
        event.data.end = event.end.valueOf();

        // render the event on the calendar
        // the last `true` argument determines if the event "sticks" (http://arshaw.com/fullcalendar/docs/event_rendering/renderEvent/)
        container.fullCalendar('renderEvent', event, true);

        $(this).remove();
        popup.open(event);
        buttons.save.enable('Save');
    };
    config.eventClick = function(event, jsEvent, view) {
        popup.open(event);
    };

    

    config.eventDragStop = config.eventResizeStop = onEventChange;

    var popup = function() {
        var popup = {};
        var modal = $('#popup');
        var options = {
            backdrop: 'static',
            keyboard: false
        };

        var save = function() {
            buttons.save.disable('Saving...');
            var form = modal.find('form');
            var event = form.data('event');
            form.find('input[name=start]').val(event.data.start);
            form.find('input[name=end]').val(event.data.end);
            var data = form.serializeArray();
            $.ajax({
                url: event.session_form_url,
                type: form.attr('method'),
                data: data,
                success: function(result) {
                    if(result.status) {
                        event.data.id = result.session_id;
                        event.saved = true;
                        modal.modal('hide');
                    }
                    else {
                        modal.find('.modal-body').html(result.form);
                        form.data('event', event);
                    }
                }
            });
        };

        modal.find('.save').on('click', save);

        popup.open = function(event) {
            $.get(event.session_form_url, event.data, function(data) {
                modal.find('.modal-body').html(data);
                modal.find('form').data('event', event);
            });
            modal.find('.modal-title').text(event.title);
            modal.find('.modal-body').html('Loading...');
            modal.modal(options);
        };


        return popup;
    }();

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

    calendar.init = function(url_list, from, to) {
        //Initialise data for calendar
        start = new Date(from);
        end = new Date(to);
        urls = url_list;

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

        //Set height of proposals column for ease of use
        proposals.height(container.find('.fc-content').height());
    };

    return calendar;
};
