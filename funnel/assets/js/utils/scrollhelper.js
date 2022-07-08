const ScrollHelper = {
  animateScrollTo(offsetY) {
    $('html,body').animate(
      {
        scrollTop: offsetY,
      },
      'slow'
    );
  },
  smoothScroll() {
    $('a.js-smooth-scroll').on('click', function clickHandler() {
      ScrollHelper.animateScrollTo($(this.hash).offset().top);
    });
  },
  getPageHeaderHeight() {
    let headerHeight;
    if ($(window).width() < window.Hasgeek.Config.mobileBreakpoint) {
      headerHeight = $('.mobile-nav').height();
    } else {
      headerHeight = $('header').height() + $('nav').height();
    }
    return headerHeight;
  },
  scrollTabs() {
    if (document.getElementById('jquery-scroll-tabs')) {
      // Horizontal scroll to active tab
      $('#jquery-scroll-tabs').animate(
        {
          scrollLeft: document.querySelector('.tabs__item--active').offsetLeft,
        },
        'slow'
      );
      $('#jquery-scroll-tabs .js-scroll-prev').on('click', (event) => {
        event.preventDefault();
        const prevTab = $('.tabs__item--active')
          .prev('.tabs__item')
          .attr('href');

        if (prevTab) {
          window.location.href = prevTab;
        }
      });
      $('#jquery-scroll-tabs .js-scroll-next').on('click', (event) => {
        event.preventDefault();
        const nextTab = $('.tabs__item--active')
          .next('.tabs__item')
          .attr('href');

        if (nextTab) {
          window.location.href = nextTab;
        }
      });
    }
  },
};

export default ScrollHelper;
