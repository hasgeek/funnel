import saveProject from './utils/bookmark';
import 'htmx.org';
import initEmbed from './utils/initembed';
import Ticketing from './utils/ticket_widget';

$(() => {
  window.Hasgeek.homeInit = function homeInit(markdownContainer, tickets = '') {
    // Expand CFP section
    $('.jquery-show-all').on('click', function showAll(event) {
      event.preventDefault();
      const projectElemClass = `.${$(this).data('projects')}`;
      $(projectElemClass).removeClass('mui--hide');
      $(this).addClass('mui--hide');
    });

    $('.js-save-form').each(function saveProjectButton() {
      const projectSaveConfig = {
        formId: $(this).attr('id'),
        postUrl: $(this).attr('action'),
      };
      saveProject(projectSaveConfig);
    });
    initEmbed(markdownContainer);

    if (tickets) {
      Ticketing.init(tickets, true);
    }
  };
});
