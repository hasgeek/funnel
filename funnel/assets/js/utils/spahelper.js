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
    window.onpopstate = function (event) {
      console.log('onpopstate', event.state);
      if (event.state && event.state.subPage) {
        Spa.fetchPage(event.state.prevUrl);
      }
    };
    this.pageTitle = pageTitle;
  },
  fetchPage(url, hightlightNavItem) {
    $.ajax({
      url,
      type: 'GET',
      success(responseData) {
        const pageDetails = {};
        const currentUrl = window.location.href;
        pageDetails.url = url;
        $('.js-spa-content').html(responseData.html);
        console.log('url', currentUrl);
        window.history.pushState(
          {
            subPage: true,
            prevUrl: currentUrl,
          },
          '',
          pageDetails.url
        );
        pageDetails.pageTitle = responseData.title
          ? `${responseData.title} – ${Spa.pageTitle}`
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
