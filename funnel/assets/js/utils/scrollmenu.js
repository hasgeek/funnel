const ScrollActiveMenu = {
  init(navId, navItemsClassName, activeMenuClassName) {
    this.navId = navId;
    this.navItemsClassName = navItemsClassName;
    this.activeMenuClassName = activeMenuClassName;
    this.navItems = [...document.querySelectorAll(`.${navItemsClassName}`)];
    this.headings = this.navItems.map((navItem) => {
      if (navItem.classList.contains('js-samepage')) {
        return document.querySelector(navItem.getAttribute('href'));
      }

      return false;
    });
    this.handleObserver = this.handleObserver.bind(this);
    this.headings.forEach((heading) => {
      if (heading) {
        const threshold =
          heading.offsetHeight / window.innerHeight > 1
            ? 0.1
            : heading.offsetHeight / window.innerHeight;
        const observer = new IntersectionObserver(this.handleObserver, {
          rootMargin: '0px',
          threshold,
        });
        observer.observe(heading);
      }
    });
    this.activeNavItem = '';
  },

  handleObserver(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const activeNavItem = this.navItems.find(
          (navItem) =>
            navItem.getAttribute('href') === `#${entry.target.getAttribute('id')}`
        );
        this.setActiveNavItem(activeNavItem);
      }
    });
  },

  setActiveNavItem(activeNavItem) {
    this.activeNavItem = activeNavItem;
    $(`.${this.navItemsClassName}`).removeClass(this.activeMenuClassName);
    activeNavItem.classList.add(this.activeMenuClassName);
    $(`#${this.navId}`).animate(
      {
        scrollLeft: activeNavItem.offsetLeft,
      },
      'slow'
    );
  },
};

export default ScrollActiveMenu;
