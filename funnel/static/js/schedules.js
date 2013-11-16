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
            pop: function() {this.container.modal(this.options);},
            hide: function() {this.container.modal('hide');},
            save: function() {
                popup.form('start').val(events.current.obj_data.start);
                popup.form('end').val(events.current.obj_data.end);
                var data = popup.form().serializeArray();
                $.ajax({
                    url: events.current.modal_url,
                    type: 'POST',
                    data: data,
                    success: function(result) {
                        if(result.status) {
                            events.update_obj_data(result.data);
                            events.current.saved = true;
                            if(events.current.unscheduled) {
                                events.current.unscheduled.remove();
                                events.current.unscheduled = null;
                            }
                            popup.hide();
                        }
                        else {
                            popup.body().html(result.form);
                        }
                    }
                });
            },
            close: function() {
                if(events.current.unscheduled) {
                    calendar.remove(events.current);
                    events.current = null;
                }
            },
            hide_save_button: function() {popup.container.find('.save').hide();},
            show_save_button: function() {popup.container.find('.save').show();}
        };

        obj.open = function() {
            SHOW_SAVE_BUTTON = false;
            $.get(events.current.modal_url, function(result) {
                popup.body().html(result);
                if(SHOW_SAVE_BUTTON) popup.show_save_button();
                else popup.hide_save_button();
            });
            popup.title().text(events.current.title);
            popup.body().html('Loading...');
            popup.pop();
        };

        obj.init = function() {
            popup.container.find('.closebutton').click(popup.close);
            popup.container.find('.save').click(popup.save);
        };

        return obj;
    }();

    var calendar = function() {
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
                        event.unscheduled = source;
                        calendar.add(event);
                        popup.open(event);
                    }
                },
                init: function(scheduled) {
                    var config = calendar.options.config;
                    config.events = scheduled;
                    if(from_date != null) {
                        config.year = from_date.getFullYear();
                        config.month = from_date.getMonth();
                        config.date = from_date.getDate();
                        if(to_date != null) {
                            config.hiddenDays = calendar.helpers.inactive_days(from_date, to_date);
                            config.firstDay = from_date.getDay();
                        }
                    }
                    config.eventClick = events.onClick;
                    config.eventResizeStop = config.eventDragStop = events.onChange;
                }
            },
            init_obj: {id: null, start: null, end: null, title: null},
            add: function(event) {
                this.container.fullCalendar('renderEvent', event, true);
                events.add_obj_data(event);
            },
            filters: {
                unsaved: function(event) {return !event.saved;}
            },
            events: function(filter) {
                if(typeof filter == 'string') return this.container.fullCalendar('clientEvents', this.filters[filter]);
                if(typeof filter == 'function') return this.container.fullCalendar('clientEvents', filter);
                return this.container.fullCalendar('clientEvents');
            },
            init: function(scheduled) {
                this.options.init(scheduled);
                this.container.fullCalendar(this.options.config);
            }
        };
        var obj = {};
        var buttons = {};

        obj.init = function(scheduled) {
            from_date = new Date(from_date);
            to_date = new Date(to_date);
            calendar.init(scheduled);
            popup.init();
        };

        obj.remove = function(event) {
            calendar.container.fullCalendar('removeEvents', event._id);
        }

        return obj;

    }();
    var events = function() {
        var events = {
            current: null,
            init_obj: {id: null, start: null, end: null, title: null},
            add_obj_data: function(event) {
                if(typeof event != 'undefined') this.current = event;
                if(this.current) {
                    obj_data = $.extend({}, this.init_obj);
                    obj_data = $.extend(obj_data, this.current.obj_data);                    
                    this.current.obj_data = obj_data;
                    this.update_time();
                };
            },
            update_obj_data: function(obj, event) {
                if(typeof event != 'undefined') this.current = event;
                if(typeof obj != 'object') return;
                if(this.current) {
                    $.extend(this.current.obj_data, obj);
                    console.log(this.current.obj_data);
                }
            },
            update_time: function(event) {
                if(typeof event != 'undefined') this.current = event;
                if(this.current) {
                    this.current.obj_data.end = this.current.end.valueOf();
                    this.current.obj_data.start = this.current.start.valueOf();
                }
            },
            onChange: function(event, jsEvent, ui, view) {
                event.saved = false;
                this.update_time(event);
            },
            onClick: function(event, jsEvent, view) {this.current = event;popup.open();},
            save: function() {}
        };

        var unscheduled_events = {
            container: $('#proposals .list'),
            add: function(element) {
                element.draggable(this.options.draggable);
                element.data('info', {
                    saved: false,
                    modal_url: element.attr('data-form-url'),
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

        for(i in scheduled) {
            scheduled[i] = {
                start: new Date(scheduled[i].start),
                end: new Date(scheduled[i].end),
                modal_url: scheduled[i].modal_url,
                title: scheduled[i].title,
                unscheduled: null,
                obj_data: scheduled[i]
            };
            delete scheduled[i].obj_data.modal_url;
        }

        return events;

    }();
    calendar.init(scheduled);
});