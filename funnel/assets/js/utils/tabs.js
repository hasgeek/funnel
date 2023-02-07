import Utils from './helper';

const hasOverflow = (el) => el.scrollLeft + el.scrollWidth > el.clientWidth;

const MUITabs = {
  async init(container) {
    const parentElement = $(container || 'body');

    // Using a ResizeObserver to mark tab bars having overflow
    // content with a class.
    const rObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        if (hasOverflow(entry.target))
          $(entry.target).parent().addClass('has-overflow');
        else $(entry.target).parent().removeClass('has-overflow');
      });
    });

    parentElement
      .find('.md-tabset .mui-tabs__bar:not(.activating):not(.activated)')
      .each(function tabsetsAccessibility() {
        // Function being called once for each tabs bar
        const tabsBar = $(this);
        tabsBar.addClass('activating');

        // http://web-accessibility.carnegiemuseums.org/code/tabs/
        let index = 0;
        const tabs = tabsBar.find('[role=tab]');
        const icons = MUITabs.createIconset();

        // Wrap the tabs bar with a container, to allow introduction of
        // tabs navigation arrow icons.
        const leftIcons = $('<div class="tabs-left-icons"></div>').html(
          Object.values(icons.left)
        );
        const rightIcons = $('<div class="tabs-right-icons"></div>').html(
          Object.values(icons.right)
        );
        tabsBar
          .wrap('<div class="mui-tabs__bar--wrapper"></div>')
          .before(leftIcons)
          .after(rightIcons);

        // Observe this tabs bar with ResizeObserver.
        rObserver.observe(tabsBar[0]);

        // Activate tab pointed by current index.
        function activateCurrent() {
          window.mui.tabs.activate($(tabs.get(index)).data('mui-controls'));
        }

        // Use IntersectionObserver to update tab element with it's
        // visibility status.
        const iObserver = new IntersectionObserver((entries) => {
          entries.forEach(
            (entry) => {
              $(entry.target).data('isIntersecting', entry.isIntersecting);
              $(entry.target).data('intersection', entry.intersectionRatio);
            },
            {
              root: tabsBar[0],
              threshold: 1,
            }
          );
        });

        // Functions to update index to previous and next tabs and
        // activate them.
        function previous() {
          if (index > 0) index -= 1;
          else index = tabs.length - 1;
          activateCurrent();
        }
        function next() {
          if (index < tabs.length - 1) index += 1;
          else index = 0;
          activateCurrent();
        }

        // Functions to scroll the tabs bar left and right.
        function scrollTo(i) {
          tabsBar[0].scrollLeft = tabs.get(i).offsetLeft - tabsBar[0].offsetLeft;
        }
        function leftScroll() {
          const tabsBarWidth = tabsBar[0].clientWidth;
          // Find the first visible tab.
          let firstVisible = 0;
          while (
            firstVisible < tabs.length - 1 &&
            !$(tabs.get(firstVisible)).data('isIntersecting')
          )
            firstVisible += 1;
          // Calculate the tab to switch to.
          let switchTo = firstVisible;
          const end = tabsBar[0].scrollLeft;
          while (
            switchTo >= 0 &&
            end - tabs.get(switchTo).parentElement.offsetLeft < tabsBarWidth
          )
            switchTo -= 1;
          scrollTo(switchTo + 1);
        }
        function rightScroll() {
          // Calculate tab to switch to.
          let switchTo = tabs.length - 1;
          while (switchTo > 0 && !$(tabs[switchTo]).data('isIntersecting'))
            switchTo -= 1;
          scrollTo(switchTo);
        }

        // Bind arrow keys to previous/next for accessibility.
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

        tabs.each(function attachTabAccessibilityEvents() {
          // Observe each tab for visibility within it's tabs bar using IntersectionObserver.
          iObserver.observe(this);
          // Attach event listeners to update accessibility attributes of tabs shown/hidden.
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

        // Bind scroll/touch actions to the arrow icons.
        $(icons.left.touch).click(previous);
        $(icons.right.touch).click(next);
        $(icons.left.scroll).click(leftScroll);
        $(icons.right.scroll).click(rightScroll);
        tabsBar.removeClass('activating').addClass('activated');
      });
  },
  createIconset() {
    return {
      left: {
        touch: this.createIcon('touch', 'left'),
        scroll: this.createIcon('scroll', 'left'),
      },
      right: {
        touch: this.createIcon('touch', 'right'),
        scroll: this.createIcon('scroll', 'right'),
      },
    };
  },
  createIcon(mode, direction) {
    return Utils.getFaiconHTML(`angle-${direction}`, 'body', true, [
      `tabs-nav-icon-${direction}`,
      `js-tabs-${mode}`,
    ]);
  },
};

export default MUITabs;
