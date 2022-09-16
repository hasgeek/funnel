import SaveProject from './utils/bookmark';
import 'htmx.org';
import MarkmapEmbed from './utils/markmap';

$(() => {
  window.Hasgeek.homeInit = function homeInit() {
    // Expand CFP section
    $('.jquery-show-all').click(function showAll(event) {
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
      SaveProject(projectSaveConfig);
    });
  };
  MarkmapEmbed.init();
});
