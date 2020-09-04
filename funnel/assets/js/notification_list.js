import Vue from 'vue/dist/vue.min';
import { Utils } from './util';

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
          observer: '',
          lazyLoader: '',
        };
      },
      methods: {
        fetchResult(page, refresh = false) {
          if (!refresh) {
            // Stop observing the lazy loader element
            notificationApp.observer.unobserve(notificationApp.lazyLoader);
          }
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
                  // Start observing the lazy loader element to fetch next page when it comes into viewport
                  notificationApp.lazyoad();
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
          if (this.lazyLoader) {
            this.handleObserver = this.handleObserver.bind(this);

            const observer = new IntersectionObserver(this.handleObserver, {
              rootMargin: '0px',
              threshold: 0,
            });
            observer.observe(this.lazyLoader);
            this.observer = observer;
          }
        },
        handleObserver(entries) {
          console.log('entries', entries);
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
              success: function (responseData) {
                notificationItem.notification.is_read = true;
                notificationItem.observer.unobserve(notification);
                Utils.setNotifyIcon(responseData.unread);
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
        this.lazyLoader = document.querySelector('.js-lazy-loader');
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
