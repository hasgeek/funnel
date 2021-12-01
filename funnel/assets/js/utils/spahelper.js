import Form from './formhelper';

const Spa = {
  pageTitle: '',
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
  handleBrowserHistory(pageTitle) {
    $(window).on('popstate', () => {
      if (window.history.state.subPage) {
        Spa.fetchPage(window.history.state.prevUrl);
      } else {
        window.history.back();
      }
    });
    this.pageTitle = pageTitle;
  },
  fetchPage(url, hightlightNavItem) {
    $.ajax({
      url,
      type: 'GET',
      success(responseData) {
        const pageDetails = {};
        pageDetails.url = url;
        $('.js-spa-content').html(responseData.html);
        window.history.pushState(
          {
            subPage: true,
            prevUrl: window.location.href,
          },
          '',
          pageDetails.url
        );
        pageDetails.pageTitle = responseData.title
          ? `${esponseData.title} – ${Spa.pageTitle}`
          : Spa.pageTitle;
        Spa.updateMetaTags(pageDetails);
        hightlightNavItem();
      },
      error(response) {
        const errorMsg = Form.getResponseError(response);
        window.toastr.error(errorMsg);
      },
    });
  },
};

export default Spa;
