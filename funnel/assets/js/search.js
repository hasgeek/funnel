import Ractive from "ractive";

const Search = {
  init(config) {
  	Ractive.DEBUG = false;
    let widget = new Ractive({
      el: '#search-wrapper',
      template: '#search-template',
      data: {
        tabs: config.counts,
        results: '',
        activeTab: '',
        pagePath: window.location.pathname,
        queryString: '',
        defaultImage: config.defaultImage
      },
      getQueryString(paramName) {
        let searchStr = window.location.search.substring(1).split('&');
        let queryString = searchStr.map((param) => {
          let paramSplit = param.split('=');
          if (paramSplit[0] === paramName) {
            return paramSplit[1];
          } else {
          	return false;
          }
        }).filter(val => val && val !== "");
        return queryString[0];
      },
      updateTabContent(event, searchType) {
        event.original.preventDefault();
        if(this.get('results.' + searchType)) {
        	let url = `${this.get('pagePath')}?q=${this.get('queryString')}&type=${searchType}`;
          this.activateTab(searchType, '', url);
        } else {
          this.fetchResult(searchType);
        }
      },
      fetchResult(searchType, page=1) {
        let url = `${this.get('pagePath')}?q=${this.get('queryString')}&type=${searchType}`
        $.ajax({
          type: 'GET',
          url: `${url}&page=${page}`,
          timeout: 5000,
          dataType: 'json',
          success: function(data) {
            widget.activateTab(searchType, data.results, url, page);
          }
        });
      },
      activateTab(searchType, result='', url='', page) {
        if(result) {
          if(page > 1) {
            let existingResults = this.get('results.' + searchType);
            let searchResults = [];
            searchResults.push(...existingResults.items);
            searchResults.push(...result.items);
            result.items = searchResults
            this.set('results.' + searchType, result);
          } else {
            this.set('results.' + searchType, result);
          }
        }
        this.set('activeTab', searchType);
        if (url) {
          this.handleBrowserHistory(searchType, url);
        }
        this.lazyoad();
      },
      handleBrowserHistory(searchType, url) {
        window.history.pushState({'searchType': searchType}, '', url);
        $(window).on('popstate', () => {
          if(window.history.state) {
            widget.set('activeTab', window.history.state.searchType)
          }
        });
      },
      updateMetaTags: function() {
      },
      lazyoad: function() {
        let lazyLoader = document.querySelector('.js-lazy-loader');
        if(lazyLoader) {
          this.handleObserver = this.handleObserver.bind(this);

          let observer = new IntersectionObserver(
            this.handleObserver,
            {
              rootMargin: '0px',
              threshold: 0.5 
            },
          );
          observer.observe(lazyLoader);
        }
      },
      handleObserver(entries) {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            let nextPage = entry.target.getAttribute('data-next-page');
            if(nextPage) {
              this.fetchResult(this.get('activeTab'), nextPage);
            }
          }
          return;
        });
      },
      initTab() {
        let queryString = this.getQueryString('q');
        this.set('queryString', queryString);
        // Fill the search box with queryString
        document.querySelector('.js-search-field').value = queryString;

        let searchType = this.getQueryString('type');
        if(searchType && config.results) {
          this.activateTab(searchType, config.results);
        } else {
        	searchType = this.get('tabs')[0]['type'];
        	console.log('searchType', searchType);
          this.fetchResult(searchType);
        }
      },
      onrender() {
        this.initTab();
      }
    });
  }
};

$(() => {
  window.HasGeek.Search = function (config) {
    Search.init(config);
  }
});
