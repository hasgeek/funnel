import { MOBILE_BREAKPOINT, NOTIFICATION_REFRESH_INTERVAL } from '../constants';
import Utils from './helper';

const ReadStatus = {
  setNotifyIcon(unread) {
    if (unread) {
      $('.header__nav-links--updates').addClass(
        'header__nav-links--updates--unread'
      );
    } else {
      $('.header__nav-links--updates').removeClass(
        'header__nav-links--updates--unread'
      );
    }
  },
  async updateNotificationStatus() {
    const response = await fetch(window.Hasgeek.Config.notificationCount, {
      headers: {
        Accept: 'application/x.html+json',
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (response && response.ok) {
      const responseData = await response.json();
      ReadStatus.setNotifyIcon(responseData.unread);
    }
  },
  async sendNotificationReadStatus() {
    const notificationID = Utils.getQueryString('utm_source');
    const Base58regex = /[\d\w]{21,22}/;

    if (notificationID && Base58regex.test(notificationID)) {
      const url = window.Hasgeek.Config.markNotificationReadUrl.replace(
        'eventid_b58',
        notificationID
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
          ReadStatus.setNotifyIcon(responseData.unread);
        }
      }
    }
  },
  headerMenuDropdown(menuBtnClass, menuWrapper, menu, url) {
    const menuBtn = $(menuBtnClass);
    const topMargin = 1;
    const headerHeight = $('.header').height() + topMargin;
    let page = 1;
    let lazyLoader;
    let observer;

    const openMenu = () => {
      if ($(window).width() < MOBILE_BREAKPOINT) {
        $(menuWrapper).find(menu).animate({ top: '0' });
      } else {
        $(menuWrapper).find(menu).animate({ top: headerHeight });
      }
      $('.header__nav-links--active').addClass('header__nav-links--menuOpen');
      menuBtn.addClass('header__nav-links--active');
      $('body').addClass('body-scroll-lock');
    };

    const closeMenu = () => {
      if ($(window).width() < MOBILE_BREAKPOINT) {
        $(menuWrapper).find(menu).animate({ top: '100vh' });
      } else {
        $(menuWrapper).find(menu).animate({ top: '-100vh' });
      }
      menuBtn.removeClass('header__nav-links--active');
      $('body').removeClass('body-scroll-lock');
      $('.header__nav-links--active').removeClass(
        'header__nav-links--menuOpen'
      );
    };

    const updatePageNumber = () => {
      page += 1;
    };

    const fetchMenu = async (pageNo = 1) => {
      const menuUrl = `${url}?${new URLSearchParams({
        page: pageNo,
      }).toString()}`;
      const response = await fetch(menuUrl, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (response && response.ok) {
        const responseData = await response.text();
        if (responseData) {
          if (observer) {
            observer.unobserve(lazyLoader);
            $('.js-load-comments').remove();
          }
          $(menuWrapper).find(menu).append(responseData);
          updatePageNumber();
          lazyLoader = document.querySelector('.js-load-comments');
          if (lazyLoader) {
            observer = new IntersectionObserver(
              (entries) => {
                entries.forEach((entry) => {
                  if (entry.isIntersecting) {
                    fetchMenu(page);
                  }
                });
              },
              {
                rootMargin: '0px',
                threshold: 0,
              }
            );
            observer.observe(lazyLoader);
          }
        }
      }
    };

    // If user logged in, preload menu
    if ($(menuWrapper).length) {
      fetchMenu();
    }

    // Open full screen account menu in mobile
    menuBtn.on('click', function clickOpenCloseMenu() {
      if ($(this).hasClass('header__nav-links--active')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    $('body').on('click', (event) => {
      const totalBtn = $(menuBtn).toArray();
      let isChildElem = false;
      totalBtn.forEach((element) => {
        isChildElem = isChildElem || $.contains(element, event.target);
      });
      if (
        $(menuBtn).hasClass('header__nav-links--active') &&
        !$(event.target).is(menuBtn) &&
        !isChildElem
      ) {
        closeMenu();
      }
    });
  },
  init() {
    ReadStatus.sendNotificationReadStatus();
    if ($('.header__nav-links--updates').length) {
      ReadStatus.updateNotificationStatus();
      window.setInterval(
        ReadStatus.updateNotificationStatus,
        NOTIFICATION_REFRESH_INTERVAL
      );
    }
  },
};

export default ReadStatus;
