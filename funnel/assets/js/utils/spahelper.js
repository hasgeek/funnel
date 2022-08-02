import Form from './formhelper';

const Spa = {
  pageTitle: '',
  hightlightNavItemFn: '',
  init(pageTitle, currentnavItem, hightlightNavItemFn) {
    this.pageTitle = pageTitle;
    this.hightlightNavItemFn = hightlightNavItemFn;
    this.handleBrowserHistory(currentnavItem);
  },
  handleBrowserHistory(currentnavItem) {
    // Store the initial content
    window.history.replaceState(
      {
        subPage: true,
        prevUrl: window.location.href,
        navId: currentnavItem,
        refresh: true,
      },
      '',
      window.location.href
    );

    $(window).on('popstate', () => {
      if (
        window.history.state &&
        window.history.state.subPage &&
        window.history.state.refresh
      ) {
        Spa.fetchPage(
          window.history.state.prevUrl,
          window.history.state.navId,
          false
        );
      }
    });
  },
  updateHistory(pageDetails) {
    window.history.pushState(
      {
        subPage: true,
        prevUrl: pageDetails.url,
        navId: pageDetails.navId,
        refresh: true,
      },
      '',
      pageDetails.url
    );
    pageDetails.pageTitle = pageDetails.title
      ? `${pageDetails.title} – ${Spa.pageTitle}`
      : Spa.pageTitle;
    Spa.updateMetaTags(pageDetails);
  },
  updateMetaTags(pageDetails) {
    if (pageDetails.title) {
      $('title').html(pageDetails.title);
    } else {
      $('title').html(pageDetails.pageTitle);
    }
    $('meta[name="DC.title"]').attr('content', pageDetails.pageTitle);
    $('meta[property="og:title"]').attr('content', pageDetails.pageTitle);
    $('meta[property="twitter:title"]').attr('content', pageDetails.pageTitle);
    if (pageDetails.description) {
      $('meta[name=description]').attr('content', pageDetails.description);
      $('meta[property="og:description"]').attr(
        'content',
        pageDetails.description
      );
    }
    $('link[rel=canonical]').attr('href', pageDetails.url);
    $('meta[property="og:url"]').attr('content', pageDetails.url);
  },
  fetchPage(url, currentNavId, updateHistory) {
    $.ajax({
      url,
      type: 'GET',
      accepts: {
        xhtmljson: 'application/x.html+json',
      },
      converters: {
        'text xhtmljson': (result) => {
          return JSON.parse(result);
        },
      },
      dataType: 'xhtmljson',
      success(responseData) {
        const pageDetails = {};
        pageDetails.url = url;
        pageDetails.navId = currentNavId;
        $('.js-spa-content').html(responseData.html);
        if (Spa.hightlightNavItemFn) Spa.hightlightNavItemFn(currentNavId);
        pageDetails.title = window.Hasgeek.subpageTitle
          ? `${window.Hasgeek.subpageTitle} – ${Spa.pageTitle}`
          : Spa.pageTitle;
        if (updateHistory) Spa.updateHistory(pageDetails);
      },
      error(response) {
        const errorMsg = Form.getResponseError(response);
        window.toastr.error(errorMsg);
      },
    });
  },
};

export default Spa;
