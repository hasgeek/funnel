import Utils from './helper';

const Tabs = {
  overflowObserver: new ResizeObserver(function checkOverflow(entries) {
    entries.forEach((entry) => {
      if (Tabs.helpers.hasOverflow(entry.target))
        $(entry.target).parent().addClass('has-overflow');
      else $(entry.target).parent().removeClass('has-overflow');
    });
  }),
  getIntersectionObserver(tablist) {
    return new IntersectionObserver((entries) => {
      entries.forEach(
        (entry) => {
          $(entry.target).data('isIntersecting', entry.isIntersecting);
        },
        {
          root: tablist,
          threshold: 1,
        }
      );
    });
  },
  wrapAndAddIcons(tablist) {
    const icons = Tabs.helpers.createIconset();
    // Wrap the tabs bar with a container, to allow introduction of
    // tabs navigation arrow icons.
    const $leftIcons = $('<div class="tabs-nav-icons-left"></div>').html(
      Object.values(icons.left)
    );
    const $rightIcons = $('<div class="tabs-nav-icons-right"></div>').html(
      Object.values(icons.right)
    );
    $(tablist)
      .wrap('<div class="md-tablist-wrapper"></div>')
      .before($leftIcons)
      .after($rightIcons);
    $(icons.left.touch).click(function previousTab() {
      tablist.dispatchEvent(new Event('previous-tab'));
    });
    $(icons.right.touch).click(function nextTab() {
      tablist.dispatchEvent(new Event('next-tab'));
    });
    $(icons.left.scroll).click(function scrollLeft() {
      tablist.dispatchEvent(new Event('scroll-left'));
    });
    $(icons.right.scroll).click(function scrollRight() {
      tablist.dispatchEvent(new Event('scroll-right'));
    });
  },
  checkScrollability() {
    // Function to update no-scroll-left and no-scroll-right
    // classes for tabs bar wrapper.
    if (!Tabs.helpers.hasLeftOverflow(this))
      $(this).parent().addClass('no-scroll-left');
    else $(this).parent().removeClass('no-scroll-left');
    if (!Tabs.helpers.hasRightOverflow(this))
      $(this).parent().addClass('no-scroll-right');
    else $(this).parent().removeClass('no-scroll-right');
  },
  getLeftScrollIndex(tablist, $tabs) {
    const tablistWidth = tablist.clientWidth;
    // Find the first visible tab.
    let firstVisible = 0;
    while (
      firstVisible < $tabs.length - 1 &&
      !$($tabs.get(firstVisible)).data('isIntersecting')
    )
      firstVisible += 1;
    // Calculate the tab to switch to.
    let switchTo = firstVisible;
    const end = tablist.scrollLeft;
    while (
      switchTo >= 0 &&
      end - $tabs.get(switchTo).parentElement.offsetLeft < tablistWidth
    )
      switchTo -= 1;
    return switchTo + 1;
  },
  getRightScrollIndex($tabs) {
    // Calculate tab to switch to.
    let switchTo = $tabs.length - 1;
    while (switchTo > 0 && !$($tabs[switchTo]).data('isIntersecting')) switchTo -= 1;
    return switchTo;
  },
  addScrollListeners(tablist, $tabs) {
    function scrollTo(i) {
      tablist.scrollLeft = $tabs.get(i).offsetLeft - tablist.offsetLeft;
    }
    tablist.addEventListener('scroll-left', function scrollLeft() {
      scrollTo(Tabs.getLeftScrollIndex(tablist, $tabs));
    });
    tablist.addEventListener('scroll-right', function scrollRight() {
      scrollTo(Tabs.getRightScrollIndex($tabs));
    });
    $(tablist).scroll(Utils.debounce(Tabs.checkScrollability, 500));
  },
  addNavListeners(tablist, $tabs) {
    let index = 0;
    function activateCurrent() {
      window.mui.tabs.activate($($tabs.get(index)).data('mui-controls'));
    }
    tablist.addEventListener('previous-tab', function previousTab() {
      if (index > 0) index -= 1;
      else index = $tabs.length - 1;
      activateCurrent();
    });
    tablist.addEventListener('next-tab', function nextTab() {
      if (index < $tabs.length - 1) index += 1;
      else index = 0;
      activateCurrent();
    });
    $tabs.each(function addTabListeners(tabIndex, tab) {
      tab.addEventListener('mui.tabs.showend', function tabActivated(ev) {
        index = tabIndex;
        ev.srcElement.scrollIntoView();
      });
    });
  },
  enhanceARIA(tablist, $tabs) {
    $tabs.on('keydown', function addArrowNav(event) {
      const [LEFT, UP, RIGHT, DOWN] = [37, 38, 39, 40];
      const k = event.which || event.keyCode;
      if (k >= LEFT && k <= DOWN) {
        switch (k) {
          case LEFT:
          case UP:
            tablist.dispatchEvent(new Event('previous-tab'));
            break;
          case RIGHT:
          case DOWN:
            tablist.dispatchEvent(new Event('next-tab'));
            break;
          default:
        }
        event.preventDefault();
      }
    });
    $tabs.each(function addTabListeners(tabIndex, tab) {
      tab.addEventListener('mui.tabs.showend', function tabActivated(ev) {
        $(ev.srcElement).attr({ tabindex: 0, 'aria-selected': 'true' }).focus();
      });
      tab.addEventListener('mui.tabs.hideend', function tabDeactivated(ev) {
        $(ev.srcElement).attr({ tabindex: -1, 'aria-selected': 'false' }).focus();
      });
    });
  },
  async processTablist(index, tablist) {
    const $tablist = $(tablist);
    const $tabs = $tablist.find('[role=tab]');
    const isMarkdown = $tablist.parent().hasClass('md-tabset');
    let visibilityObserver;
    let $tablistContainer;
    Tabs.addNavListeners(tablist, $tabs);
    if (isMarkdown) {
      $tablist.addClass('mui-tabs__bar');
      Tabs.addScrollListeners(tablist, $tabs);
      Tabs.wrapAndAddIcons(tablist);
      $tablistContainer = $tablist.parent();
      Tabs.overflowObserver.observe(tablist);
      visibilityObserver = Tabs.getIntersectionObserver(tablist);
      Tabs.checkScrollability.bind(tablist)();
    }
    $tabs.each(function processTab(tabIndex, tab) {
      if (isMarkdown) {
        $(tab)
          .attr('data-mui-toggle', 'tab')
          .attr('data-mui-controls', $(tab).attr('aria-controls'));
        visibilityObserver.observe(tab);
        const $panel = $(`#${$(tab).attr('aria-controls')}`);
        $panel.mouseenter(
          $tablistContainer.addClass.bind($tablistContainer, 'has-panel-hover')
        );
        $panel.mouseleave(
          $tablistContainer.removeClass.bind($tablistContainer, 'has-panel-hover')
        );
      }
    });
    Tabs.enhanceARIA(tablist, $tabs);
    $tablist.addClass('activated').removeClass('activating');
  },
  process($parentElement, $tablists) {
    $parentElement.find('.md-tabset [role=tabpanel]').addClass('mui-tabs__pane');
    $parentElement.find('.md-tabset .md-tab-active').addClass('mui--is-active');
    $tablists.each(this.processTablist);
  },
  async init(container) {
    const $parentElement = $(container || 'body');
    const $tablists = $parentElement.find(
      '[role=tablist]:not(.activating, .activated)'
    );
    $tablists.addClass('activating');
    this.process($parentElement, $tablists);
  },
  helpers: {
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
    hasOverflow(el) {
      return el.scrollLeft + el.scrollWidth > el.clientWidth;
    },
    hasLeftOverflow(el) {
      return Boolean(el.scrollLeft);
    },
    hasRightOverflow(el) {
      return (
        el.scrollLeft + el.clientWidth + el.offsetLeft <
        el.children[el.children.length - 1].offsetLeft +
          el.children[el.children.length - 1].clientWidth
      );
    },
  },
};

export default Tabs;
