import Vue from 'vue/dist/vue.min';

const Notification = {
  init({ markReadUrl, divElem }) {
    const notificationApp = new Vue({
      el: divElem,
      data() {
        return {
          notifications: [],
          eventids: [],
          next_num: 1,
          waitingForResponse: false,
          markReadUrl: markReadUrl,
        };
      },
      methods: {
        fetchResult(page, refresh = false) {
          if (!notificationApp.waitingForResponse) {
            notificationApp.waitingForResponse = true;
            $.ajax({
              type: 'GET',
              data: {
                page: page,
              },
              timeout: window.Hasgeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                notificationApp.addNotifications(data.notifications, refresh);
                if (!refresh) {
                  if (data.next_num) {
                    notificationApp.next_num = data.next_num;
                  } else {
                    notificationApp.next_num = 0;
                  }
                }
                notificationApp.waitingForResponse = false;
              },
            });
          }
        },
        addNotifications(notifications, refresh) {
          notifications.forEach((notice) => {
            if (
              !notificationApp.eventids.includes(notice.notification.eventid)
            ) {
              if (refresh) {
                notificationApp.notifications.unshift(notice);
              } else {
                notificationApp.notifications.push(notice);
              }
              notificationApp.eventids.push(notice.notification.eventid);
            }
          });
        },
        lazyoad() {
          const lazyLoader = document.querySelector('.js-lazy-loader');
          if (lazyLoader) {
            this.handleObserver = this.handleObserver.bind(this);

            const observer = new IntersectionObserver(this.handleObserver, {
              rootMargin: '0px',
              threshold: 0,
            });
            observer.observe(lazyLoader);
          }
        },
        handleObserver(entries) {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.fetchResult(notificationApp.next_num);
            }
          });
        },
        updateReadStatus(notification) {
          if ($(notification).attr('data-visible-time')) {
            let notificationItem = this.notifications[
              $(notification).attr('data-index')
            ];
            let url = this.markReadUrl.replace(
              'eventid',
              notificationItem.notification.eventid
            );
            $.ajax({
              type: 'POST',
              url: url,
              data: {
                csrf_token: $('meta[name="csrf-token"]').attr('content'),
              },
              dataType: 'json',
              timeout: window.Hasgeek.config.ajaxTimeout,
              success: function () {
                notificationItem.notification.is_read = true;
                notificationItem.observer.unobserve(notification);
              },
            });
          }
        },
        notificationInViewport(entries) {
          let app = this;
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              $(entry.target).attr('data-visible-time', entry.time);
              window.setTimeout(function () {
                app.updateReadStatus(entry.target);
              }, window.Hasgeek.config.readReceiptTimeout);
            } else {
              $(entry.target).attr('data-visible-time', '');
            }
          });
        },
      },
      mounted() {
        this.lazyoad();
        window.setInterval(() => {
          this.fetchResult(1, true);
        }, window.Hasgeek.config.refreshInterval);
      },
      updated() {
        let app = this;
        $.each($('.update--unread'), function (index, elem) {
          app.notificationInViewport = app.notificationInViewport.bind(app);
          const notificationObserver = new IntersectionObserver(
            app.notificationInViewport,
            {
              rootMargin: '0px',
              threshold: 0,
            }
          );
          notificationObserver.observe(elem);
          let notificationItem = app.notifications[$(elem).attr('data-index')];
          notificationItem.observer = notificationObserver;
        });
      },
    });
  },
};

$(() => {
  window.Hasgeek.Notification = function (config) {
    Notification.init(config);
  };
});
