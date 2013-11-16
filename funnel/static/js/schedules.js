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