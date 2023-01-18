const MarkdownMUITabs = {
  async init(container) {
    const parentElement = $(container || 'body');

    parentElement
      .find('.md-tabset .mui-tabs__bar')
      .each(function tabsetsAccessibility() {
        let index = 0;
        const tabs = $(this).find('[role=tab]');
        // http://web-accessibility.carnegiemuseums.org/code/tabs/
        tabs.bind({
          keydown: function onpress(event) {
            const LEFT_ARROW = 37;
            const UP_ARROW = 38;
            const RIGHT_ARROW = 39;
            const DOWN_ARROW = 40;
            const k = event.which || event.keyCode;

            if (k >= LEFT_ARROW && k <= DOWN_ARROW) {
              if (k === LEFT_ARROW || k === UP_ARROW) {
                if (index > 0) index -= 1;
                else index = tabs.length - 1;
              } else if (k === RIGHT_ARROW || k === DOWN_ARROW) {
                if (index < tabs.length - 1) index += 1;
                else index = 0;
              }
              window.mui.tabs.activate($(tabs.get(index)).data('mui-controls'));
            }
          },
        });
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
      });
    // parentElement.find('[data-mui-controls^="md-tab-"]').each(function attach() {
    //   this.addEventListener('mui.tabs.showend', function showingTab(ev) {
    //     console.log(ev);
    //   });
    // });
  },
};

export default MarkdownMUITabs;
