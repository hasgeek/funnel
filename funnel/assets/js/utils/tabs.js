import Utils from './helper';

const hasOverflow = (el) => el.scrollLeft + el.scrollWidth > el.clientWidth;
const hasLeftOverflow = (el) => Boolean(el.scrollLeft);
const hasRightOverflow = (el) =>
  el.scrollLeft + el.clientWidth + el.offsetLeft <
  el.children[el.children.length - 1].offsetLeft +
    el.children[el.children.length - 1].clientWidth;

const MUITabs = {
  // ResizeObserver to mark tab bars having overflow, with a class.
  resizeObserver: new ResizeObserver((entries) => {
    entries.forEach((entry) => {
      if (hasOverflow(entry.target)) $(entry.target).parent().addClass('has-overflow');
      else $(entry.target).parent().removeClass('has-overflow');
    });
  }),
  getIntersectionObserver(tabsBar) {
    return new IntersectionObserver((entries) => {
      entries.forEach(
        (entry) => {
          $(entry.target).data('isIntersecting', entry.isIntersecting);
          $(entry.target).data('intersection', entry.intersectionRatio);
        },
        {
          root: tabsBar,
          threshold: 1,
        }
      );
    });
  },
  wrapAndAddIcons(tabsBar, icons) {
    // Wrap the tabs bar with a container, to allow introduction of
    // tabs navigation arrow icons.
    const $leftIcons = $('<div class="tabs-nav-icons-left"></div>').html(
      Object.values(icons.left)
    );
    const $rightIcons = $('<div class="tabs-nav-icons-right"></div>').html(
      Object.values(icons.right)
    );
    $(tabsBar)
      .wrap('<div class="mui-tabs__bar--wrapper"></div>')
      .before($leftIcons)
      .after($rightIcons);
  },
  getLeftScrollIndex(tabsBar, tabs) {
    const tabsBarWidth = tabsBar.clientWidth;
    // Find the first visible tab.
    let firstVisible = 0;
    while (
      firstVisible < tabs.length - 1 &&
      !$(tabs.get(firstVisible)).data('isIntersecting')
    )
      firstVisible += 1;
    // Calculate the tab to switch to.
    let switchTo = firstVisible;
    const end = tabsBar.scrollLeft;
    while (
      switchTo >= 0 &&
      end - tabs.get(switchTo).parentElement.offsetLeft < tabsBarWidth
    )
      switchTo -= 1;
    return switchTo;
  },
  getRightScrollIndex(tabs) {
    // Calculate tab to switch to.
    let switchTo = tabs.length - 1;
    while (switchTo > 0 && !$(tabs[switchTo]).data('isIntersecting')) switchTo -= 1;
    return switchTo;
  },
  checkScrollability(tabsBar) {
    // Function to update no-scroll-left and no-scroll-right
    // classes for tabs bar wrapper.
    if (!hasLeftOverflow(tabsBar)) $(tabsBar).parent().addClass('no-scroll-left');
    else $(tabsBar).parent().removeClass('no-scroll-left');
    if (!hasRightOverflow(tabsBar)) $(tabsBar).parent().addClass('no-scroll-right');
    else $(tabsBar).parent().removeClass('no-scroll-right');
  },
  async init(container) {
    const $parentElement = $(container || 'body');
    $parentElement
      .find('.mui-tabs__bar:not(.activating-aria):not(.activated-aria)')
      .each(function handleTabsetARIA() {
        const tabsBar = this;
        $(tabsBar).addClass('activating-aria');
        // http://web-accessibility.carnegiemuseums.org/code/tabs/
        let index = 0;
        const $tabs = $(tabsBar).find('[role=tab]');
        tabsBar.addEventListener('previousTab', function previousTab(ev) {
          if (index > 0) index -= 1;
          else index = $tabs.length - 1;
          ev.target.dispatchEvent(new Event('activateCurrent'));
        });
        tabsBar.addEventListener('nextTab', function nextTab(ev) {
          if (index < $tabs.length - 1) index += 1;
          else index = 0;
          ev.target.dispatchEvent(new Event('activateCurrent'));
        });
        tabsBar.addEventListener('activateCurrent', function activateCurrent() {
          window.mui.tabs.activate($($tabs.get(index)).data('mui-controls'));
        });
        // Bind arrow keys to previous/next for accessibility.
        $tabs.bind({
          keydown: function onpress(event) {
            const LEFT_ARROW = 37;
            const UP_ARROW = 38;
            const RIGHT_ARROW = 39;
            const DOWN_ARROW = 40;
            const k = event.which || event.keyCode;

            if (k >= LEFT_ARROW && k <= DOWN_ARROW) {
              if (k === LEFT_ARROW || k === UP_ARROW)
                tabsBar.dispatchEvent(new Event('previousTab'));
              else if (k === RIGHT_ARROW || k === DOWN_ARROW)
                tabsBar.dispatchEvent(new Event('nextTab'));
              event.preventDefault();
            }
          },
        });
        $tabs.each(function handleTab() {
          const tab = this;
          // Attach event listeners to update accessibility attributes of tabs shown/hidden.
          tab.addEventListener('mui.tabs.showend', function ariaActive(ev) {
            $(ev.srcElement).attr({ tabindex: 0, 'aria-selected': 'true' }).focus();
            index = [...$tabs].indexOf(ev.srcElement);
            ev.srcElement.scrollIntoViewIfNeeded();

            // Uncomment to enable hiding of nav on
            // non-touch devices, when first / last tab
            // is activated. This will need more work at init, if enabled.

            // if (index === 0) $tabsBarContainer.addClass('tabs-active-first');
            // else $tabsBarContainer.removeClass('tabs-active-first');
            // if (index === $tabs.length - 1)
            //   $tabsBarContainer.addClass('tabs-active-last');
            // else $tabsBarContainer.removeClass('tabs-active-last');
          });
          tab.addEventListener('mui.tabs.hideend', function ariaInactive(ev) {
            $(ev.srcElement).attr({ tabindex: '-1', 'aria-selected': 'false' });
          });
        });
        $(tabsBar).removeClass('activating-aria').addClass('activated-aria');
      });
    $parentElement
      .find('.md-tabset .mui-tabs__bar:not(.activating):not(.activated)')
      .each(function handleTabset() {
        // Function being called once for each tabs bar
        const tabsBar = this;
        $(tabsBar).addClass('activating');
        const $tabs = $(tabsBar).find('[role=tab]');
        const icons = MUITabs.createIconset();

        MUITabs.wrapAndAddIcons(tabsBar, icons);
        // $tabsBarContainer should be initialised after calling wrapAndAddIcons.
        const $tabsBarContainer = $(tabsBar).parent();

        // Observe this tabs bar with ResizeObserver.
        MUITabs.resizeObserver.observe(tabsBar);

        // Use IntersectionObserver to update tab element with it's
        // visibility status.
        const observer = MUITabs.getIntersectionObserver(tabsBar);

        // Attach this to the scroll event.
        $(tabsBar).scroll(
          Utils.debounce(MUITabs.checkScrollability, 500, this, tabsBar)
        );

        // Functions to scroll the tabs bar left and right.
        function scrollTo(i) {
          tabsBar.scrollLeft = $tabs.get(i).offsetLeft - tabsBar.offsetLeft;
        }
        function leftScroll() {
          scrollTo(MUITabs.getLeftScrollIndex(tabsBar, $tabs) + 1);
        }
        function rightScroll() {
          scrollTo(MUITabs.getRightScrollIndex($tabs));
        }

        $tabs.each(function handleTab() {
          const tab = this;
          // Observe each tab for visibility within it's tabs
          // bar using IntersectionObserver.
          observer.observe(tab);

          // Toggle has-panel-hover on the tabs bar wrapper
          // when a related panel is in hover state.
          const $panel = $(`#${$(tab).data('mui-controls')}`);
          $panel.mouseenter(
            $tabsBarContainer.addClass.bind($tabsBarContainer, 'has-panel-hover')
          );
          $panel.mouseleave(
            $tabsBarContainer.removeClass.bind($tabsBarContainer, 'has-panel-hover')
          );
        });

        // Bind scroll/touch actions to the arrow icons.
        $(icons.left.touch).click(function previousTab() {
          tabsBar.dispatchEvent(new Event('previousTab'));
        });
        $(icons.right.touch).click(function nextTab() {
          tabsBar.dispatchEvent(new Event('nextTab'));
        });
        $(icons.left.scroll).click(leftScroll);
        $(icons.right.scroll).click(rightScroll);

        // Update scrollability classes for tabs bar wrapper.
        MUITabs.checkScrollability(tabsBar);

        $(tabsBar).removeClass('activating').addClass('activated');
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
