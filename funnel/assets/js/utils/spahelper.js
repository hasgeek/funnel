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
      },
      '',
      window.location.href
    );

    $(window).on('popstate', () => {
      if (window.history.state && window.history.state.subPage) {
        Spa.fetchPage(
          window.history.state.prevUrl,
          window.history.state.navId,
          false
        );
      } else {
        window.history.back();
      }
    });
  },
  updateHistory(pageDetails) {
    window.history.pushState(
      {
        subPage: true,
        prevUrl: pageDetails.url,
        navId: pageDetails.navId,
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
      success(responseData) {
        const pageDetails = {};
        pageDetails.url = url;
        pageDetails.navId = currentNavId;
        $('.js-spa-content').html(responseData.html);
        if (Spa.hightlightNavItemFn) Spa.hightlightNavItemFn(currentNavId);
        pageDetails.title = window.Hasgeek.subpageTitle;
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
