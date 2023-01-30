import Utils from './helper';

const MUITabs = {
  async init(container) {
    const parentElement = $(container || 'body');

    parentElement.find('.mui-tabs__bar').each(function tabsetsAccessibility() {
      // http://web-accessibility.carnegiemuseums.org/code/tabs/
      let index = 0;
      const tabs = $(this).find('[role=tab]');
      function activateCurrent() {
        window.mui.tabs.activate($(tabs.get(index)).data('mui-controls'));
      }
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
        this.addEventListener('mui.tabs.showend', function addListenerToShownTab(ev) {
          $(ev.srcElement).attr({ tabindex: 0, 'aria-selected': 'true' }).focus();
        });
        this.addEventListener('mui.tabs.hideend', function addListenerToHiddenTab(ev) {
          $(ev.srcElement).attr({ tabindex: '-1', 'aria-selected': 'false' });
        });

        // const iconElements = document.querySelectorAll('.overflow-icon');

        // if (iconElements.length > 2) {
        //   const lastIcon = iconElements[iconElements.length - 1];
        //   lastIcon.parentNode.removeChild(lastIcon);

        //   const secondlastIcon = iconElements[iconElements.length - 2];
        //   secondlastIcon.parentNode.removeChildElement(secondlastIcon);
        // }

        // const wrapperElements = document.querySelectorAll('.tabs__icon-wrapper');

        // if (wrapperElements.length > 1) {
        //   const lastWrapperElement = wrapperElements[wrapperElements.length - 1];
        //   lastWrapperElement.parentNode.removeChild(lastWrapperElement);
        //   console.log(wrapperElements.length);
        // }
      });
    });

    const tabsBar = document.querySelector('.mui-tabs__bar');
    console.log(tabsBar.scrollWidth, tabsBar.clientWidth);

    if (tabsBar.scrollWidth - tabsBar.clientWidth > 0) {
      const iconWrapper = document.createElement('div');
      const overflowIconLeft = Utils.getFaiconHTML('angle-left', 'body', true, [
        'overflow-icon',
      ]);
      const overflowIconRight = Utils.getFaiconHTML('angle-right', 'body', true, [
        'overflow-icon',
      ]);

      const tabsContainer = tabsBar.parentNode;

      iconWrapper.setAttribute('class', 'tabs__icon-wrapper');

      tabsContainer.replaceChild(iconWrapper, tabsBar);
      iconWrapper.appendChild(tabsBar);

      tabsBar.insertAdjacentElement('beforebegin', overflowIconLeft);
      tabsBar.insertAdjacentElement('afterend', overflowIconRight);
    }

    // parentElement.find('[data-mui-controls^="md-tab-"]').each(function attach() {
    //   this.addEventListener('mui.tabs.showend', function showingTab(ev) {
    //     console.log(ev);
    //   });
    // });
  },
};

export default MUITabs;
