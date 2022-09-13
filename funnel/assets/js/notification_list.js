import Vue from 'vue/dist/vue.min';
import Utils from './utils/helper';

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
          markReadUrl,
          observer: '',
          lazyLoader: '',
        };
      },
      methods: {
        async fetchResult(page, refresh = false) {
          if (!refresh) {
            // Stop observing the lazy loader element
            notificationApp.observer.unobserve(notificationApp.lazyLoader);
          }
          if (!notificationApp.waitingForResponse) {
            notificationApp.waitingForResponse = true;
            const url = `${window.location.href}?${new URLSearchParams({
              page,
            }).toString()}`;
            const response = await fetch(url, {
              headers: {
                Accept: 'application/json',
              },
            });
            if (response && response.ok) {
              const data = await response.json();
              if (data) {
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
              }
            }
          }
        },
        addNotifications(notifications, refresh) {
          notifications.forEach((notice) => {
            if (!notificationApp.eventids.includes(notice.notification.eventid_b58)) {
              if (refresh) {
                notificationApp.notifications.unshift(notice);
              } else {
                notificationApp.notifications.push(notice);
              }
              notificationApp.eventids.push(notice.notification.eventid_b58);
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
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.fetchResult(notificationApp.next_num);
            }
          });
        },
        async updateReadStatus(notification) {
          if ($(notification).attr('data-visible-time')) {
            const notificationItem =
              this.notifications[$(notification).attr('data-index')];
            const url = this.markReadUrl.replace(
              'eventid_b58',
              notificationItem.notification.eventid_b58
            );
            const response = await fetch(url, {
              method: 'POST',
              headers: {
                Accept: 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
              },
              body: new URLSearchParams({
                csrf_token: $('meta[name="csrf-token"]').attr('content'),
              }).toString(),
            });
            if (response && response.ok) {
              const responseData = await response.json();
              if (responseData) {
                notificationItem.notification.is_read = true;
                notificationItem.observer.unobserve(notification);
                Utils.setNotifyIcon(responseData.unread);
              }
            }
          }
        },
        notificationInViewport(entries) {
          const app = this;
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              $(entry.target).attr('data-visible-time', entry.time);
              window.setTimeout(() => {
                app.updateReadStatus(entry.target);
              }, window.Hasgeek.Config.readReceiptTimeout);
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
        }, window.Hasgeek.Config.refreshInterval);
      },
      updated() {
        const app = this;
        $.each($('.update--unread'), (index, elem) => {
          app.notificationInViewport = app.notificationInViewport.bind(app);
          const notificationObserver = new IntersectionObserver(
            app.notificationInViewport,
            {
              rootMargin: '0px',
              threshold: 0,
            }
          );
          notificationObserver.observe(elem);
          const notificationItem = app.notifications[$(elem).attr('data-index')];
          notificationItem.observer = notificationObserver;
        });
      },
    });
  },
};

$(() => {
  window.Hasgeek.notificationInit = (config) => {
    Notification.init(config);
  };
});
