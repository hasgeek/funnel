import { MOBILE_BREAKPOINT } from '../constants';

const LazyLoadMenu = {
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
      $('.header__nav-links--active').removeClass('header__nav-links--menuOpen');
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
    LazyLoadMenu.headerMenuDropdown(
      '.js-menu-btn',
      '.js-account-menu-wrapper',
      '.js-account-menu',
      window.Hasgeek.Config.accountMenu
    );
    if (window.Hasgeek.Config.commentSidebarElem) {
      LazyLoadMenu.headerMenuDropdown(
        '.js-comments-btn',
        '.js-comments-wrapper',
        '.js-comment-sidebar',
        window.Hasgeek.Config.unreadCommentUrl
      );
    }
  },
};

export default LazyLoadMenu;
