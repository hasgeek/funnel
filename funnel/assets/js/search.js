import Ractive from 'ractive';

const Search = {
  init(config) {
    Ractive.DEBUG = false;
    const widget = new Ractive({
      el: '#search-wrapper',
      template: '#search-template',
      data: {
        tabs: config.counts,
        results: '',
        activeTab: '',
        pagePath: window.location.pathname,
        queryString: '',
        defaultImage: config.defaultImage,
        formatTime(date) {
          const d = new Date(date);
          return d.toLocaleTimeString('default', {
            hour: 'numeric',
            minute: 'numeric',
          });
        },
        formatDate(date) {
          const d = new Date(date);
          return d.toLocaleDateString('default', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          });
        },
        dateString(date) {
          return date.substr(-2);
        },
      },
      getQueryString(paramName) {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has(paramName)) {
          return urlParams.get(paramName);
        }
        return false;
      },
      updateTabContent(searchType) {
        if (this.get(`results.${searchType}`)) {
          const url = `${this.get('pagePath')}?q=${this.get(
            'queryString'
          )}&type=${searchType}`;
          this.activateTab(searchType, '', url);
        } else {
          this.fetchResult(searchType);
        }
      },
      fetchResult(searchType, page = 1) {
        const url = `${this.get('pagePath')}?q=${this.get(
          'queryString'
        )}&type=${searchType}`;
        $.ajax({
          type: 'GET',
          url: `${url}&page=${page}`,
          timeout: window.HasGeek.config.ajaxTimeout,
          dataType: 'json',
          success(data) {
            widget.activateTab(searchType, data.results, url, page);
          },
        });
      },
      activateTab(searchType, result = '', url = '', page) {
        if (result) {
          if (page > 1) {
            const existingResults = this.get(`results.${searchType}`);
            const searchResults = [];
            searchResults.push(...existingResults.items);
            searchResults.push(...result.items);
            result.items = searchResults;
            this.set(`results.${searchType}`, result);
          } else {
            this.set(`results.${searchType}`, result);
          }
        }
        this.set('activeTab', searchType);
        $('#scrollable-tabs').animate(
          {
            scrollLeft: document.querySelector('.tabs__item--active')
              .offsetLeft,
          },
          'slow'
        );
        if (url) {
          this.handleBrowserHistory(url);
        }
        this.updateMetaTags(searchType, url);
        this.lazyoad();
      },
      handleBrowserHistory(url = '') {
        window.history.replaceState('', '', url);
      },
      updateMetaTags(searchType, url = '') {
        const q = this.get('queryString');
        const { count } = this.get(`results.${searchType}`);
        const title = `Search results: ${q}`;
        const description = `${count} results found for "${q}"`;

        $('title').html(title);
        $('meta[name=DC\\.title]').attr('content', title);
        $('meta[property=og\\:title]').attr('content', title);
        $('meta[name=description]').attr('content', description);
        $('meta[property=og\\:description]').attr('content', description);
        if (url) {
          $('link[rel=canonical]').attr('href', url);
          $('meta[property=og\\:url]').attr('content', url);
        }
      },
      lazyoad() {
        const lazyLoader = document.querySelector('.js-lazy-loader');
        if (lazyLoader) {
          this.handleObserver = this.handleObserver.bind(this);

          const observer = new IntersectionObserver(this.handleObserver, {
            rootMargin: '0px',
            threshold: 0.5,
          });
          observer.observe(lazyLoader);
        }
      },
      handleObserver(entries) {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const nextPage = entry.target.getAttribute('data-next-page');
            if (nextPage) {
              this.fetchResult(this.get('activeTab'), nextPage);
            }
          }
        });
      },
      getCurrentTabIndex() {
        return this.get('tabs').findIndex(
          tab => tab.type === this.get('activeTab')
        );
      },
      swipe(action) {
        const tabs = this.get('tabs');
        const activeTabIndex = this.getCurrentTabIndex();
        if (
          activeTabIndex + action >= 0 &&
          activeTabIndex + action < tabs.length
        ) {
          this.updateTabContent(tabs[activeTabIndex + action].type);
        }
      },
      initTab() {
        const queryString = this.getQueryString('q');
        this.set('queryString', queryString);
        // Fill the search box with queryString
        document.querySelector('.js-search-field').value = queryString;

        let searchType = this.getQueryString('type');
        if (searchType && config.results) {
          this.activateTab(searchType, config.results);
        } else {
          searchType = this.get('tabs')[0].type;
          this.fetchResult(searchType);
        }
      },
      onrender() {
        this.initTab();
      },
    });
  },
};

$(() => {
  window.HasGeek.Search = function(config) {
    Search.init(config);
  };
});
