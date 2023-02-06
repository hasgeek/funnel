import Utils from './helper';

const MUITabs = {
  async init(container) {
    const parentElement = $(container || 'body');

    parentElement
      .find('.md-tabset .mui-tabs__bar:not(.activating):not(.activated)')
      .each(function tabsetsAccessibility() {
        $(this).addClass('activating');
        // http://web-accessibility.carnegiemuseums.org/code/tabs/
        let index = 0;
        const tabs = $(this).find('[role=tab]');
        const tabSet = $(this).parent();
        // CREATING TOUCH ICON TOGGLE
        function toggleTouchIcon() {
          if (index === 0) {
            tabSet
              .find('.overflow-icon-left.js-tab-touch')
              .addClass('hidden-overflowIcon');
            tabSet
              .find('.overflow-icon-right.js-tab-touch')
              .removeClass('hidden-overflowIcon');
          } else if (index > 0 && index < tabs.length - 1) {
            tabSet
              .find('.overflow-icon-left.js-tab-touch')
              .removeClass('hidden-overflowIcon');
            tabSet
              .find('.overflow-icon-right.js-tab-touch')
              .removeClass('hidden-overflowIcon');
          } else {
            tabSet
              .find('.overflow-icon-left.js-tab-touch')
              .removeClass('hidden-overflowIcon');
            tabSet
              .find('.overflow-icon-right.js-tab-touch')
              .addClass('hidden-overflowIcon');
          }
        }
        // DEFINING SCROLL ICON TOGGLE FUNCTION
        function toggleScrollIcon() {
          const tabsBar = tabSet.find('.mui-tabs__bar');
          const scrollVal = Math.ceil(tabsBar.scrollLeft());
          const maxScrollWidth = tabsBar[0].scrollWidth - tabsBar[0].clientWidth;

          if (scrollVal <= 0) {
            tabsBar
              .parent()
              .find('.overflow-icon-left.js-tab-scroll')
              .css('visibility', 'hidden');

            tabsBar
              .parent()
              .find('.overflow-icon-right.js-tab-scroll')
              .css('visibility', 'visible');
          } else
            tabsBar
              .parent()
              .find('.overflow-icon-left.js-tab-scroll')
              .css('visibility', 'visible');

          if (maxScrollWidth - scrollVal <= 1) {
            tabsBar
              .parent()
              .find('.overflow-icon-right.js-tab-scroll')
              .css('visibility', 'hidden');

            tabsBar
              .parent()
              .find('.overflow-icon-left.js-tab-scroll')
              .css('visibility', 'visible');
          } else
            tabsBar
              .parent()
              .find('.overflow-icon-right.js-tab-scroll')
              .css('visibility', 'visible');
        }
        // ACTIVATING CURRENT ELEMENT
        function activateCurrent() {
          window.mui.tabs.activate($(tabs.get(index)).data('mui-controls'));
        }
        // FUNCTIONS FOR NAVIGATING TABSBAR ON KEYPRESS
        function previous() {
          if (index > 0) {
            index -= 1;
            toggleTouchIcon();
          } else {
            index = tabs.length - 1;
            toggleTouchIcon();
          }
          activateCurrent();
        }
        function next() {
          if (index < tabs.length - 1) {
            index += 1;
            toggleTouchIcon();
          } else {
            index = 0;
            toggleTouchIcon();
          }
          activateCurrent();
        }
        // KEYPRESS EVENTHANDLER FOR EACH TAB INSTANCE
        tabs.bind({
          keydown: function onpress(event) {
            const LEFT_ARROW = 37;
            const UP_ARROW = 38;
            const RIGHT_ARROW = 39;
            const DOWN_ARROW = 40;
            const k = event.which || event.keyCode;

            if (k >= LEFT_ARROW && k <= DOWN_ARROW) {
              if (k === LEFT_ARROW || k === UP_ARROW) previous();
              else if (k === RIGHT_ARROW || k === DOWN_ARROW) next();
              event.preventDefault();
            }
          },
        });
        // CLICK EVENTHANDLER FOR EACH TAB INSTANCE
        tabs.bind('click', () => {
          setTimeout(() => {
            index = $(this).find('li.mui--is-active').index();
            toggleTouchIcon();
          }, 100);
        });
        // EVENT LISTENERS FOR ACCESSIBILITY EVENTS
        tabs.each(function attachTabAccessibilityEvents() {
          this.addEventListener('mui.tabs.showend', function addListenerToShownTab(ev) {
            $(ev.srcElement).attr({ tabindex: 0, 'aria-selected': 'true' }).focus();
          });
          this.addEventListener(
            'mui.tabs.hideend',
            function addListenerToHiddenTab(ev) {
              $(ev.srcElement).attr({ tabindex: '-1', 'aria-selected': 'false' });
            }
          );
        });
        // CREATING OVERFLOW ICONS FOR TOUCH AND SCROLL
        if ($(this).prop('scrollWidth') - $(this).prop('clientWidth') > 0) {
          const overflowTouchIconLeft = Utils.getFaiconHTML(
            'angle-left',
            'body',
            true,
            ['overflow-icon', 'overflow-icon-left', 'js-tab-touch']
          );
          const overflowTouchIconRight = Utils.getFaiconHTML(
            'angle-right',
            'body',
            true,
            ['overflow-icon', 'overflow-icon-right', 'js-tab-touch']
          );
          const overflowScrollIconLeft = Utils.getFaiconHTML(
            'angle-left',
            'body',
            false,
            ['overflow-icon', 'overflow-icon-left', 'js-tab-scroll']
          );
          const overflowScrollIconRight = Utils.getFaiconHTML(
            'angle-right',
            'body',
            true,
            ['overflow-icon', 'overflow-icon-right', 'js-tab-scroll']
          );
          // WRAPPING THE ICONS AND TABSBAR
          $(this).wrap('<div class="tabs__icon-wrapper"></div>');
          // ADDING THE ICONS BEFORE AND AFTER THE TABSBAR
          $(this).before(overflowTouchIconLeft);
          $(this).after(overflowTouchIconRight);
          $(this).before(overflowScrollIconLeft);
          $(this).after(overflowScrollIconRight);
          // TOGGLING NECESSARY ICONS
          toggleTouchIcon();
          toggleScrollIcon();
        }
        // DEFINING SCROLL FUNCTIONS
        function scrollIconLeft() {
          $(this).parent().find('.mui-tabs__bar').animate({ scrollLeft: '-=80' }, 100);
          setTimeout(toggleScrollIcon, 200);
        }
        function scrollIconRight() {
          $(this).parent().find('.mui-tabs__bar').animate({ scrollLeft: '+=80' }, 100);
          setTimeout(toggleScrollIcon, 200);
        }
        // CREATING OVERFLOW TOUCH ICONS
        $(this).parent().find('.overflow-icon-left.js-tab-touch').click(previous);
        $(this).parent().find('.overflow-icon-right.js-tab-touch').click(next);
        // CREATING OVERFLOW SCROLL ICONS
        $(this)
          .parent()
          .find('.overflow-icon-left.js-tab-scroll')
          .click(scrollIconLeft);
        $(this)
          .parent()
          .find('.overflow-icon-right.js-tab-scroll')
          .click(scrollIconRight);
      });

    // parentElement.find('[data-mui-controls^="md-tab-"]').each(function attach() {
    //   this.addEventListener('mui.tabs.showend', function showingTab(ev) {
    //     console.log(ev);
    //   });
    // });

    $(this).removeClass('activating').addClass('activated');
  },
};

export default MUITabs;
