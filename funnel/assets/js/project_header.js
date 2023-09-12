import SaveProject from './utils/bookmark';
import Video from './utils/embedvideo';
import Spa from './utils/spahelper';
import { Widgets } from './utils/form_widgets';
import initEmbed from './utils/initembed';
import SortItem from './utils/sort';
import Ticketing from './utils/ticket_widget';

$(() => {
  window.Hasgeek.projectHeaderInit = (
    projectTitle,
    saveProjectConfig = '',
    tickets = '',
    toggleId = '',
    sort = '',
    rsvpModalHash = 'register-modal'
  ) => {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    $('body').on('click', '.js-htmltruncate-expand', function expandTruncation(event) {
      event.preventDefault();
      $(this).addClass('mui--hide');
      $(this).next('.js-htmltruncate-full').removeClass('mui--hide');
      initEmbed($(this).next('.js-htmltruncate-full'));
    });

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function addEmbedVideoPlayer() {
        const videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }

    $('a.js-register-btn').click(function showRegistrationModal() {
      window.history.pushState(
        {
          openModal: true,
        },
        '',
        `#${rsvpModalHash}`
      );
    });

    if (window.location.hash.includes(rsvpModalHash)) {
      $('a.js-register-btn').modal('show');
    }

    if (tickets) {
      Ticketing.init(tickets);
    }

    if (toggleId) {
      Widgets.activateToggleSwitch(toggleId);
    }

    if (sort?.url) {
      SortItem($(sort.wrapperElem), sort.placeholder, sort.url);
    }

    const hightlightNavItem = (navElem) => {
      const navHightlightClass = 'sub-navbar__item--active';
      $('.sub-navbar__item').removeClass(navHightlightClass);
      $(`#${navElem}`).addClass(navHightlightClass);

      if (window.Hasgeek.subpageTitle) {
        $('body').addClass('subproject-page');
        if (window.Hasgeek.subpageHasVideo) {
          $('body').addClass('mobile-hide-livestream');
        } else {
          $('body').removeClass('mobile-hide-livestream');
        }
      } else {
        $('body').removeClass('subproject-page').removeClass('mobile-hide-livestream');
      }
    };

    const currentnavItem = $('.sub-navbar__item--active').attr('id');
    Spa.init(projectTitle, currentnavItem, hightlightNavItem);

    $('body').on('click', '.js-spa-navigate', function pageRefresh(event) {
      event.preventDefault();
      const url = $(this).attr('href');
      Spa.fetchPage(url, $(this).attr('id'), true);
    });
  };
});
